from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.correction import Correction


class CorrectionDAO(BaseDAO[Correction]):
    def __init__(self, db: Session):
        super().__init__(db, Correction)

    def get_by_question_id(self, question_id: int) -> Correction | None:
        return self.db.query(Correction).filter(Correction.question_id == question_id).first()
