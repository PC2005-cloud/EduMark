from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.task import Task


class TaskDAO(BaseDAO[Task]):
    def __init__(self, db: Session):
        super().__init__(db, Task)

    def get_by_task_id(self, task_id: str) -> Task | None:
        return self.db.query(Task).filter(Task.task_id == task_id).first()

    def list_by_user_id(self, user_id: int, page: int = 1, page_size: int = 10):
        return self.list(page=page, page_size=page_size, user_id=user_id)
