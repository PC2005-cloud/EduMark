from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.user import User


class UserDAO(BaseDAO[User]):
    def __init__(self, db: Session):
        super().__init__(db, User)

    def get_by_account(self, account: str) -> User | None:
        return self.db.query(User).filter(User.account == account).first()
