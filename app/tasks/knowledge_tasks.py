import logging
import time

from sqlalchemy.orm import Session

from app.clients.mineru import mineru_client, ContentType
from app.clients.minio import minio_client
from app.clients.bailian import bailian
from app.clients.qdrant import qdrant
from app.dao.knowledge_dao import KnowledgeDAO
from app.models import SessionLocal
from app.models.knowledge import Knowledge
from app.tasks.celery_app import celery_app
from qdrant_client.http.models import PointStruct

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3, serializer="pickle")
def knowledge_parse(self, file_data: bytes, filename: str, user_id: int,
                    subject: str | None = None, grade: str | None = None) -> int:
    logger.info("知识解析任务开始: filename=%s size=%d user_id=%d", filename, len(file_data), user_id)
    db: Session = SessionLocal()
    knowledge_id = None

    try:
        # 1. 存 MinIO
        object_name = f"knowledge/{user_id}/{int(time.time())}_{filename}"
        minio_client.ensure_bucket()
        minio_client.upload(object_name, file_data)
        logger.info("文件已存入 MinIO: %s", object_name)

        # 2. 建 Knowledge 记录
        knowledge = Knowledge(
            user_id=user_id, title=filename, url=object_name,
            subject=subject, grade=grade, status="parsing",
        )
        knowledge = KnowledgeDAO(db).create(knowledge)
        db.commit()
        knowledge_id = knowledge.id
        logger.info("Knowledge 记录已创建: id=%d", knowledge_id)

        # 3. MinerU 上传解析
        batch_id = mineru_client.upload_and_parse(file_data, filename)
        logger.info("MinerU 提交成功: batch_id=%s", batch_id)

        # 4. 轮询
        deadline = time.time() + 300
        while True:
            result = mineru_client.get_zip_urls(batch_id)
            if result.success:
                break
            if time.time() > deadline:
                raise TimeoutError("MinerU 解析超时")
            time.sleep(5)

        # 5. 解析结果
        items = mineru_client.handle_parse_result(result.zip_urls, process_images=True)

        # 6. 分块 + 向量化 + 写入 Qdrant
        texts = []
        for item in items:
            if item.type == ContentType.TEXT and item.text:
                texts.append(item.text)

        qdrant.ensure_collection()
        points = []
        for i, text in enumerate(texts):
            vec = bailian.embed([text])[0]
            points.append(PointStruct(
                id=int(f"{knowledge_id}{i:04d}"),
                vector=vec,
                payload={
                    "document_id": knowledge_id,
                    "content": text[:500],
                    "subject": subject or "",
                    "grade": grade or "",
                    "seq_in_doc": i,
                },
            ))

        if points:
            qdrant.upsert(points)

        # 7. 更新 Knowledge 记录
        knowledge = KnowledgeDAO(db).get_by_id(knowledge_id)
        if knowledge:
            knowledge.status = "completed"
            knowledge.chunk = len(points)
            db.commit()

        logger.info("知识解析完成: knowledge_id=%d chunks=%d", knowledge_id, len(points))
        return knowledge_id

    except Exception as e:
        logger.error("知识解析失败: %s", e, exc_info=True)
        db.rollback()
        if knowledge_id:
            kn = KnowledgeDAO(db).get_by_id(knowledge_id)
            if kn:
                kn.status = "failed"
                db.commit()
        raise
    finally:
        db.close()
