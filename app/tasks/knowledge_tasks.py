import logging
import time

from sqlalchemy.orm import Session

from app.clients.mineru import mineru_client, ContentType
from app.clients.minio import minio_client
from app.clients.bailian import bailian
from app.clients.qdrant import qdrant
from app.dao.knowledge_dao import KnowledgeDAO
from app.models import SessionLocal
from app.tasks.celery_app import celery_app
from qdrant_client.http.models import PointStruct

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, max_retries=3)
def knowledge_parse(self, knowledge_id: int) -> int:
    logger.info("知识解析任务开始: knowledge_id=%d", knowledge_id)
    db: Session = SessionLocal()

    try:
        # 1. 查记录
        knowledge = KnowledgeDAO(db).get_by_id(knowledge_id)
        if not knowledge:
            raise ValueError(f"Knowledge 记录不存在: {knowledge_id}")
        knowledge.status = "parsing"
        db.commit()
        logger.info("Knowledge 记录: title=%s url=%s subject=%s", knowledge.title, knowledge.url, knowledge.subject)

        # 2. 从 MinIO 下载文件
        file_data = minio_client.download(knowledge.url)
        logger.info("文件已下载: %s size=%d", knowledge.url, len(file_data))

        # 3. MinerU 上传解析
        batch_id = mineru_client.upload_and_parse(file_data, knowledge.title)
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
                    "subject": knowledge.subject or "",
                    "grade": knowledge.grade or "",
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
        kn = KnowledgeDAO(db).get_by_id(knowledge_id)
        if kn:
            kn.status = "failed"
            db.commit()
        raise
    finally:
        db.close()
