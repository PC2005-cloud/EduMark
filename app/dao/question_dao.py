from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.question import Question


class QuestionDAO(BaseDAO[Question]):
    def __init__(self, db: Session):
        super().__init__(db, Question)

    def list_by_task_id(self, task_id: str) -> list[Question]:
        return self.db.query(Question).filter(Question.task_id == task_id).all()
