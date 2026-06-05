import logging

from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.knowledge import Knowledge

logger = logging.getLogger(__name__)


class KnowledgeDAO(BaseDAO[Knowledge]):
    def __init__(self, db: Session):
        super().__init__(db, Knowledge)

    def cascade_delete(self, knowledge_id: int):
        from app.clients.minio import minio_client
        from app.clients.qdrant import qdrant
        from app.models.question_chunk import QuestionChunk

        kn = self.get_by_id(knowledge_id)
        if not kn:
            return
        if kn.url:
            try:
                minio_client.delete(kn.url)
            except Exception:
                pass
        try:
            self.db.query(QuestionChunk).filter(
                QuestionChunk.knowledge_id == knowledge_id
            ).delete()
            chunk_ids = [int(f"{knowledge_id}{i:04d}") for i in range(max(kn.chunk, 1))]
            qdrant._http.post(
                f"/collections/knowledge_chunks/points/delete",
                json={"points": chunk_ids},
                timeout=30,
            )
        except Exception as e:
            logger.warning("Qdrant 删除失败: %s", e)
        self.delete(knowledge_id)
