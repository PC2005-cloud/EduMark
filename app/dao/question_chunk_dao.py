from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.question_chunk import QuestionChunk


class QuestionChunkDAO(BaseDAO[QuestionChunk]):
    def __init__(self, db: Session):
        super().__init__(db, QuestionChunk)

    def list_by_question_id(self, question_id: int) -> list[QuestionChunk]:
        return self.db.query(QuestionChunk).filter(QuestionChunk.question_id == question_id).all()
