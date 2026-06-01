from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Image(Base):
    __tablename__ = "image"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    update_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
