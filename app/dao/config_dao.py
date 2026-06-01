from sqlalchemy.orm import Session

from app.dao import BaseDAO
from app.models.config import Config


class ConfigDAO(BaseDAO[Config]):
    def __init__(self, db: Session):
        super().__init__(db, Config)

    def get_by_user_id(self, user_id: int) -> Config | None:
        return self.db.query(Config).filter(Config.user_id == user_id).first()
