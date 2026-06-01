import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.response import PageDTO, Result
from app.dao.correction_dao import CorrectionDAO
from app.models import get_db
from app.models.correction import Correction
from app.schemas import CorrectionCreate, CorrectionUpdate, CorrectionOut

logger = logging.getLogger(__name__)


@router_v1.get("/corrections/{id}")
def get_correction(id: int, db: Session = Depends(get_db)):
    logger.info("查询批改结果, id=%d", id)
    c = CorrectionDAO(db).get_by_id(id)
    return Result.success(CorrectionOut.model_validate(c)) if c else Result.error("not found")


@router_v1.post("/corrections")
def create_correction(data: CorrectionCreate, db: Session = Depends(get_db)):
    logger.info("创建批改结果, question_id=%d", data.question_id)
    c = Correction(**data.model_dump())
    return Result.success(CorrectionOut.model_validate(CorrectionDAO(db).create(c)))


@router_v1.put("/corrections/{id}")
def update_correction(id: int, data: CorrectionUpdate, db: Session = Depends(get_db)):
    logger.info("更新批改结果, id=%d", id)
    c = CorrectionDAO(db).update(id, data.model_dump(exclude_unset=True))
    return Result.success(CorrectionOut.model_validate(c)) if c else Result.error("not found")


@router_v1.delete("/corrections/{id}")
def delete_correction(id: int, db: Session = Depends(get_db)):
    logger.info("删除批改结果, id=%d", id)
    ok = CorrectionDAO(db).delete(id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post("/corrections/page")
def page_correction(dto: PageDTO, db: Session = Depends(get_db)):
    logger.info("分页查询批改结果, page=%d size=%d", dto.page_num, dto.page_size)
    result = CorrectionDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [CorrectionOut.model_validate(r) for r in result.rows]
    return Result.success(result)
