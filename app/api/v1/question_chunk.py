import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.response import PageDTO, Result
from app.dao.question_chunk_dao import QuestionChunkDAO
from app.models import get_db
from app.models.question_chunk import QuestionChunk
from app.schemas import QuestionChunkCreate, QuestionChunkOut

logger = logging.getLogger(__name__)


@router_v1.get("/question-chunks/{id}")
def get_question_chunk(id: int, db: Session = Depends(get_db)):
    logger.info("查询题目知识块关联, id=%d", id)
    qc = QuestionChunkDAO(db).get_by_id(id)
    return Result.success(QuestionChunkOut.model_validate(qc)) if qc else Result.error("not found")


@router_v1.post("/question-chunks")
def create_question_chunk(data: QuestionChunkCreate, db: Session = Depends(get_db)):
    logger.info("创建题目知识块关联, question_id=%d", data.question_id)
    qc = QuestionChunk(**data.model_dump())
    return Result.success(QuestionChunkOut.model_validate(QuestionChunkDAO(db).create(qc)))


@router_v1.delete("/question-chunks/{id}")
def delete_question_chunk(id: int, db: Session = Depends(get_db)):
    logger.info("删除题目知识块关联, id=%d", id)
    ok = QuestionChunkDAO(db).delete(id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post("/question-chunks/page")
def page_question_chunk(dto: PageDTO, db: Session = Depends(get_db)):
    logger.info("分页查询题目知识块关联, page=%d size=%d", dto.page_num, dto.page_size)
    result = QuestionChunkDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [QuestionChunkOut.model_validate(r) for r in result.rows]
    return Result.success(result)
