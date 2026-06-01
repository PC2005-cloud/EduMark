from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class QuestionChunk(Base):
    __tablename__ = "question_chunk"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    question_id: Mapped[int] = mapped_column(Integer, nullable=False)
    knowledge_id: Mapped[int] = mapped_column(Integer, nullable=False)
    chunk_id: Mapped[str] = mapped_column(String(36), nullable=False)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    update_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
