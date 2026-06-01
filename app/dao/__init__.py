from typing import Generic, TypeVar

from sqlalchemy.orm import Session

from app.core.response import PageVO

T = TypeVar("T")


class BaseDAO(Generic[T]):
    def __init__(self, db: Session, model: type[T]):
        self.db = db
        self.model = model

    def get_by_id(self, id: int) -> T | None:
        return self.db.get(self.model, id)

    def create(self, entity: T) -> T:
        self.db.add(entity)
        self.db.flush()
        self.db.refresh(entity)
        return entity

    def update(self, id: int, data: dict) -> T | None:
        entity = self.get_by_id(id)
        if not entity:
            return None
        for k, v in data.items():
            setattr(entity, k, v)
        self.db.flush()
        return entity

    def delete(self, id: int) -> bool:
        entity = self.get_by_id(id)
        if not entity:
            return False
        self.db.delete(entity)
        self.db.flush()
        return True

    def list(self, page: int = 1, page_size: int = 10, **filters) -> PageVO:
        q = self.db.query(self.model)
        for col, val in filters.items():
            if val is not None and hasattr(self.model, col):
                q = q.filter(getattr(self.model, col) == val)
        total = q.count()
        rows = q.offset((page - 1) * page_size).limit(page_size).all()
        return PageVO(total=total, rows=rows)
