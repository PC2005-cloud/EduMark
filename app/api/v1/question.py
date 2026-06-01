import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.response import PageDTO, Result
from app.dao.question_dao import QuestionDAO
from app.models import get_db
from app.models.question import Question
from app.schemas import QuestionCreate, QuestionUpdate, QuestionOut

logger = logging.getLogger(__name__)


@router_v1.get("/questions/{id}")
def get_question(id: int, db: Session = Depends(get_db)):
    logger.info("查询题目, id=%d", id)
    q = QuestionDAO(db).get_by_id(id)
    return Result.success(QuestionOut.model_validate(q)) if q else Result.error("not found")


@router_v1.post("/questions")
def create_question(data: QuestionCreate, db: Session = Depends(get_db)):
    logger.info("创建题目, task_id=%s no=%s", data.task_id, data.no)
    q = Question(**data.model_dump())
    return Result.success(QuestionOut.model_validate(QuestionDAO(db).create(q)))


@router_v1.put("/questions/{id}")
def update_question(id: int, data: QuestionUpdate, db: Session = Depends(get_db)):
    logger.info("更新题目, id=%d", id)
    q = QuestionDAO(db).update(id, data.model_dump(exclude_unset=True))
    return Result.success(QuestionOut.model_validate(q)) if q else Result.error("not found")


@router_v1.delete("/questions/{id}")
def delete_question(id: int, db: Session = Depends(get_db)):
    logger.info("删除题目, id=%d", id)
    ok = QuestionDAO(db).delete(id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post("/questions/page")
def page_question(dto: PageDTO, db: Session = Depends(get_db)):
    logger.info("分页查询题目, page=%d size=%d", dto.page_num, dto.page_size)
    result = QuestionDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [QuestionOut.model_validate(r) for r in result.rows]
    return Result.success(result)
