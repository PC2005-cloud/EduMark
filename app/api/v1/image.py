import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.response import PageDTO, Result
from app.dao.image_dao import ImageDAO
from app.models import get_db
from app.models.image import Image
from app.schemas import ImageCreate, ImageOut

logger = logging.getLogger(__name__)


@router_v1.get("/images/{id}")
def get_image(id: int, db: Session = Depends(get_db)):
    logger.info("查询图片, id=%d", id)
    img = ImageDAO(db).get_by_id(id)
    return Result.success(ImageOut.model_validate(img)) if img else Result.error("not found")


@router_v1.post("/images")
def create_image(data: ImageCreate, db: Session = Depends(get_db)):
    logger.info("创建图片, task_id=%s url=%s", data.task_id, data.url)
    img = Image(**data.model_dump())
    return Result.success(ImageOut.model_validate(ImageDAO(db).create(img)))


@router_v1.delete("/images/{id}")
def delete_image(id: int, db: Session = Depends(get_db)):
    logger.info("删除图片, id=%d", id)
    ok = ImageDAO(db).delete(id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post("/images/page")
def page_image(dto: PageDTO, db: Session = Depends(get_db)):
    logger.info("分页查询图片, page=%d size=%d", dto.page_num, dto.page_size)
    result = ImageDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [ImageOut.model_validate(r) for r in result.rows]
    return Result.success(result)
