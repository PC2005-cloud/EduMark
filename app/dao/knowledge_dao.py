from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.knowledge import Knowledge


class KnowledgeDAO(BaseDAO[Knowledge]):
    def __init__(self, db: Session):
        super().__init__(db, Knowledge)
