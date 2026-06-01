from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.model import Model


class ModelDAO(BaseDAO[Model]):
    def __init__(self, db: Session):
        super().__init__(db, Model)
