from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.image import Image


class ImageDAO(BaseDAO[Image]):
    def __init__(self, db: Session):
        super().__init__(db, Image)

    def list_by_task_id(self, task_id: str) -> list[Image]:
        return self.db.query(Image).filter(Image.task_id == task_id).all()
