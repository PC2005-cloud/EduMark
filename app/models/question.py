from datetime import datetime

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class Question(Base):
    __tablename__ = "question"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(36), nullable=False)
    no: Mapped[str] = mapped_column(String(8), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=True)
    student_answer: Mapped[str] = mapped_column(Text, nullable=True)
    question_type: Mapped[str] = mapped_column(String(16), nullable=True)
    create_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
    update_time: Mapped[datetime] = mapped_column(DateTime, nullable=True)
