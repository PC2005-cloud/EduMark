import logging
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed

from sqlalchemy.orm import Session

from app.clients.minio import minio_client
from app.clients.aliyun_ocr import aliyun_ocr
from app.clients.bailian import bailian
from app.clients.qdrant import qdrant
from app.dao.config_dao import ConfigDAO
from app.dao.task_dao import TaskDAO
from app.dao.image_dao import ImageDAO
from app.dao.question_dao import QuestionDAO
from app.dao.block_dao import BlockDAO
from app.dao.correction_dao import CorrectionDAO
from app.models import SessionLocal
from app.models.task import Task
from app.models.image import Image
from app.models.question import Question
from app.models.block import Block
from app.models.correction import Correction
from app.modules.image.processor import preprocess
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_MAX_WORKERS = 5


@celery_app.task(bind=True, max_retries=3, serializer="pickle")
def homework_grading(self, files: list[tuple[bytes, str]],
                     user_id: int, subject: str | None = None,
                     grade: str | None = None) -> str:
    logger.info("批改任务开始: user_id=%d files=%d subject=%s", user_id, len(files), subject)
    db: Session = SessionLocal()
    task_id = ""
    image_urls = []

    try:
        # 1. 存 MinIO
        minio_client.ensure_bucket()
        for data, fname in files:
            url = f"homework/{user_id}/{int(time.time())}_{fname}"
            minio_client.upload(url, data)
            image_urls.append(url)
        logger.info("图片已存入 MinIO: %d 张", len(image_urls))

        # 2. 建 Task
        task_uuid = str(uuid.uuid4())
        task = Task(
            task_id=task_uuid, user_id=user_id,
            subject=subject, grade=grade,
            mode="aliyun", status="processing",
        )
        task = TaskDAO(db).create(task)
        db.commit()
        task_id = task.task_id
        logger.info("Task 已创建: task_id=%s", task_id)

        # 3. 建 Image 记录
        for url in image_urls:
            img = Image(task_id=task_id, url=url)
            ImageDAO(db).create(img)
        db.commit()

        # 4. 读 Config
        config = ConfigDAO(db).get_by_user_id(user_id)
        rec_mode = config.rec_mode if config else "aliyun"
        enable_enhance = config.enable_enhance if config else True
        enable_knowledge = config.enable_knowledge if config else True
        vl_model = config.vl_model if config and config.vl_model else "qwen-vl-plus"
        gl_model = config.gl_model if config and config.gl_model else "qwen-plus"
        task.mode = rec_mode
        db.commit()
        logger.info("用户配置: rec_mode=%s enable_enhance=%s enable_knowledge=%s",
                     rec_mode, enable_enhance, enable_knowledge)

        # 5. 多线程 OCR 识别
        def ocr_one(img_bytes: bytes) -> list:
            if enable_enhance:
                try:
                    img_bytes = preprocess(img_bytes)
                except Exception as e:
                    logger.warning("预处理失败: %s", e)
            if rec_mode == "aliyun":
                try:
                    return aliyun_ocr.cut_paper(img_bytes)
                except Exception as e:
                    logger.warning("切题失败(跳过): %s", e)
                    return []
            else:
                try:
                    results = bailian.recognize_question([img_bytes], model=vl_model)
                    items = []
                    for r in results:
                        obj = type("", (), {"text": "", "x1": 0, "y1": 0, "x2": 0, "y2": 0})()
                        obj.text = r.question
                        obj.answer = r.answer
                        obj.type = r.type
                        items.append(obj)
                    return items
                except Exception as e:
                    logger.warning("百炼识别失败: %s", e)
                    return []

        all_questions = []
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = [executor.submit(ocr_one, data) for data, _ in files]
            for future in as_completed(futures):
                all_questions.extend(future.result())

        logger.info("OCR 识别完成: %d 道题", len(all_questions))

        # 保存题目到数据库
        question_list = []
        for i, q in enumerate(all_questions, 1):
            quest = Question(
                task_id=task_id, no=str(i),
                question_text=getattr(q, "text", None) or "",
                student_answer=getattr(q, "answer", None) or "",
                question_type=getattr(q, "type", None) or "",
            )
            quest = QuestionDAO(db).create(quest)
            if hasattr(q, "x1") and (q.x1 or q.y1 or q.x2 or q.y2):
                block = Block(question_id=quest.id, url="", x1=q.x1, y1=q.y1, x2=q.x2, y2=q.y2)
                BlockDAO(db).create(block)
            question_list.append(quest)
        db.commit()
        logger.info("题目已保存: %d 道", len(question_list))

        # 6. 多线程批改（子线程不碰 ORM，只传纯数据）
        def grade_one(quest_id: int, text: str, answer: str) -> Correction | None:
            if not text:
                return None
            chunks = None
            if enable_knowledge:
                try:
                    vec = bailian.embed([text])[0]
                    sf = {"subject": subject} if subject else None
                    results = qdrant.search(vec, top_k=3, filter_conditions=sf)
                    chunks = [r.get("payload", {}).get("content", "") for r in results]
                except Exception as e:
                    logger.warning("知识检索失败: question_id=%d %s", quest_id, e)
            try:
                g = bailian.grade_question(text, answer or "", knowledge_chunks=chunks, model=gl_model)
                try:
                    score_val = float(g.score) if g.score else 0
                except (ValueError, TypeError):
                    score_val = 0
                return Correction(question_id=quest_id, score=score_val,
                                  result=g.result or "partial", comment=g.comment, analysis=g.analysis)
            except Exception as e:
                logger.warning("批改失败: question_id=%d %s", quest_id, e)
                return None

        corrections = []
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = [executor.submit(grade_one, q.id, q.question_text, q.student_answer or "")
                       for q in question_list]
            for future in as_completed(futures):
                c = future.result()
                if c:
                    corrections.append(c)

        for c in corrections:
            CorrectionDAO(db).create(c)
        db.commit()
        logger.info("批改完成: %d/%d 题", len(corrections), len(question_list))

        # 7. 完成
        task.status = "completed"
        db.commit()
        logger.info("任务完成: task_id=%s", task_id)
        return task_id

    except Exception as e:
        logger.error("批改失败: %s", e, exc_info=True)
        db.rollback()
        if task_id:
            t = TaskDAO(db).get_by_task_id(task_id)
            if t:
                t.status = "failed"
                db.commit()
        raise
    finally:
        db.close()
