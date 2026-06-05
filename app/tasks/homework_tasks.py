import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

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
from app.models.question import Question
from app.models.block import Block
from app.models.correction import Correction
from app.models.question_chunk import QuestionChunk
from app.modules.image.processor import preprocess
from app.tasks.celery_app import celery_app

logger = logging.getLogger(__name__)

_MAX_WORKERS = 10


@celery_app.task(bind=True, max_retries=3)
def homework_grading(self, task_id: str) -> str:
    logger.info("批改任务开始: task_id=%s", task_id)
    db: Session = SessionLocal()

    try:
        # 1. 查 Task
        task = TaskDAO(db).get_by_task_id(task_id)
        if not task:
            raise ValueError(f"Task 不存在: {task_id}")
        task.status = "processing"
        db.commit()
        logger.info("Task: user_id=%d subject=%s grade=%s", task.user_id, task.subject, task.grade)

        # 2. 读 Config
        config = ConfigDAO(db).get_by_user_id(task.user_id)
        rec_mode = config.rec_mode if config else "aliyun"
        enable_enhance = config.enable_enhance if config else True
        enable_knowledge = config.enable_knowledge if config else True
        vl_model = config.vl_model if config and config.vl_model else "qwen-vl-plus"
        gl_model = config.gl_model if config and config.gl_model else "qwen-plus"
        task.mode = vl_model if rec_mode == "bailian" else rec_mode
        db.commit()

        # 3. 从 MinIO 下载图片
        images = ImageDAO(db).list_by_task_id(task_id)
        files = []
        for img in images:
            data = minio_client.download(img.url)
            fname = Path(img.url).name
            files.append((data, img.url, fname))
        logger.info("图片已下载: %d 张", len(files))

        # 4. 多线程 OCR
        def ocr_one(img_bytes: bytes, img_url: str) -> list:
            if enable_enhance:
                try:
                    img_bytes = preprocess(img_bytes)
                except Exception as e:
                    logger.warning("预处理失败: %s", e)
            if rec_mode == "aliyun":
                try:
                    items = aliyun_ocr.cut_paper(img_bytes)
                    for it in items:
                        it.img_url = img_url
                    return items
                except Exception as e:
                    logger.warning("切题失败(跳过): %s", e)
                    return []
            else:
                try:
                    results = bailian.recognize_question([img_bytes], model=vl_model)
                    items = []
                    for r in results:
                        b = r.bbox or [0, 0, 0, 0]
                        if len(b) >= 4 and b[0] > 1:
                            b = [round(v / 1000, 4) for v in b]
                        obj = type("", (), {"text": "", "x1": 0, "y1": 0, "x2": 0, "y2": 0})()
                        obj.text = r.question
                        obj.answer = r.answer
                        obj.type = r.type
                        obj.img_url = img_url
                        obj.x1, obj.y1, obj.x2, obj.y2 = b[:4]
                        items.append(obj)
                    return items
                except Exception as e:
                    logger.warning("百炼识别失败: %s", e)
                    return []

        all_questions = []
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = [executor.submit(ocr_one, data, url) for data, url, _ in files]
            for future in as_completed(futures):
                all_questions.extend(future.result())

        # 保存题目
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
                url = getattr(q, "img_url", "") or ""
                block = Block(question_id=quest.id, url=url, x1=q.x1, y1=q.y1, x2=q.x2, y2=q.y2)
                BlockDAO(db).create(block)
            question_list.append(quest)
        db.commit()

        # 5. 多线程批改
        def grade_one(quest_id: int, text: str, answer: str) -> tuple[Correction | None, list]:
            if not text:
                return None, []
            chunk_refs = []
            if enable_knowledge:
                try:
                    vec = bailian.embed([text])[0]
                    sf = {"subject": task.subject} if task.subject else None

                    # 阶段一：搜 child（句子），按 parent_id 聚合取最高分
                    child_filter = dict(sf or {})
                    child_filter["node_type"] = "child"
                    child_results = qdrant.search(vec, top_k=3, score_threshold=0.1, filter_conditions=child_filter)

                    parent_scores: dict[int, float] = {}
                    for r in child_results:
                        p = r.get("payload", {})
                        parent_id = p.get("parent_id")
                        score = r.get("score", 0)
                        if parent_id is not None:
                            if parent_id not in parent_scores or score > parent_scores[parent_id]:
                                parent_scores[parent_id] = score

                    # 阶段二：按 parent_id 批量取 parent 段落，复用 child 最高分
                    if parent_scores:
                        parent_points = qdrant.get_points_by_ids(list(parent_scores.keys()))
                        for pp in parent_points:
                            p = pp.get("payload", {})
                            pid = pp.get("id")
                            chunk_refs.append({
                                "knowledge_id": p.get("document_id"),
                                "content": p.get("content", ""),
                                "chunk_id": pid,
                                "score": parent_scores.get(pid, 0),
                            })
                except Exception as e:
                    logger.warning("知识检索失败: question_id=%d %s", quest_id, e)
            try:
                chunks = [c["content"] for c in chunk_refs if c.get("content")]
                g = bailian.grade_question(text, answer or "", knowledge_chunks=chunks or None, model=gl_model)
                try:
                    score_val = float(g.score) if g.score else 0
                except (ValueError, TypeError):
                    score_val = 0
                corr = Correction(question_id=quest_id, score=score_val,
                                  result=g.result or "partial", comment=g.comment, analysis=g.analysis)
                return corr, chunk_refs
            except Exception as e:
                logger.warning("批改失败: question_id=%d %s", quest_id, e)
                return None, []

        corrections = []
        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = [executor.submit(grade_one, q.id, q.question_text, q.student_answer or "")
                       for q in question_list]
            for future in as_completed(futures):
                corr, refs = future.result()
                if corr:
                    CorrectionDAO(db).create(corr)
                    for ref in refs:
                        kid = ref.get("knowledge_id")
                        chunk_id = ref.get("chunk_id")
                        if kid and chunk_id is not None:
                            db.add(QuestionChunk(
                                question_id=corr.question_id, knowledge_id=kid, chunk_id=str(chunk_id),
                            ))
                    corrections.append(corr)
        db.commit()

        # 6. 完成
        task.status = "completed"
        db.commit()
        logger.info("批改完成: task_id=%s 题目=%d 批改=%d", task_id, len(question_list), len(corrections))
        return task_id

    except Exception as e:
        logger.error("批改失败: %s", e, exc_info=True)
        db.rollback()
        t = TaskDAO(db).get_by_task_id(task_id)
        if t:
            t.status = "failed"
            db.commit()
        raise
    finally:
        db.close()
