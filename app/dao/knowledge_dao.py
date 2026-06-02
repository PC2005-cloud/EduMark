from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.knowledge import Knowledge


class KnowledgeDAO(BaseDAO[Knowledge]):
    def __init__(self, db: Session):
        super().__init__(db, Knowledge)

    def cascade_delete(self, knowledge_id: int):
        from app.clients.minio import minio_client
        from app.clients.qdrant import qdrant

        kn = self.get_by_id(knowledge_id)
        if not kn:
            return
        if kn.url:
            try:
                minio_client.delete(kn.url)
            except Exception:
                pass
        try:
            qdrant.delete({"document_id": knowledge_id})
        except Exception:
            pass
        self.delete(knowledge_id)
