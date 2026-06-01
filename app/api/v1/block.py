import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.response import PageDTO, Result
from app.dao.block_dao import BlockDAO
from app.models import get_db
from app.models.block import Block
from app.schemas import BlockCreate, BlockOut

logger = logging.getLogger(__name__)


@router_v1.get("/blocks/{id}")
def get_block(id: int, db: Session = Depends(get_db)):
    logger.info("查询题目块, id=%d", id)
    b = BlockDAO(db).get_by_id(id)
    return Result.success(BlockOut.model_validate(b)) if b else Result.error("not found")


@router_v1.post("/blocks")
def create_block(data: BlockCreate, db: Session = Depends(get_db)):
    logger.info("创建题目块, question_id=%s", data.question_id)
    b = Block(**data.model_dump())
    return Result.success(BlockOut.model_validate(BlockDAO(db).create(b)))


@router_v1.delete("/blocks/{id}")
def delete_block(id: int, db: Session = Depends(get_db)):
    logger.info("删除题目块, id=%d", id)
    ok = BlockDAO(db).delete(id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post("/blocks/page")
def page_block(dto: PageDTO, db: Session = Depends(get_db)):
    logger.info("分页查询题目块, page=%d size=%d", dto.page_num, dto.page_size)
    result = BlockDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [BlockOut.model_validate(r) for r in result.rows]
    return Result.success(result)
