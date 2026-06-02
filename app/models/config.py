from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Config(Base):
    __tablename__ = "config"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(Integer, unique=True, nullable=False)
    rec_mode: Mapped[str] = mapped_column(String(16), nullable=False, default="aliyun")
    enable_enhance: Mapped[bool] = mapped_column(Boolean, default=True)
    vl_model: Mapped[str] = mapped_column(String(64), nullable=True)
    gl_model: Mapped[str] = mapped_column(String(64), nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    update_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
