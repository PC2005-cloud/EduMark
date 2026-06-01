from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.block import Block


class BlockDAO(BaseDAO[Block]):
    def __init__(self, db: Session):
        super().__init__(db, Block)

    def list_by_question_id(self, question_id: int) -> list[Block]:
        return self.db.query(Block).filter(Block.question_id == question_id).all()
