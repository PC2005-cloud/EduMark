import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import get_current_user
from app.core.response import PageDTO, Result
from app.dao.config_dao import ConfigDAO
from app.models import get_db
from app.models.config import Config
from app.schemas import ConfigCreate, ConfigUpdate, ConfigOut

logger = logging.getLogger(__name__)


@router_v1.get("/config/me")
def get_my_config(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info("查询当前用户配置, user_id=%s", current_user["id"])
    c = ConfigDAO(db).get_by_user_id(current_user["id"])
    return Result.success(ConfigOut.model_validate(c)) if c else Result.error("not found")


@router_v1.put("/config/me")
def update_my_config(data: ConfigUpdate, current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info("更新当前用户配置, user_id=%s", current_user["id"])
    dao = ConfigDAO(db)
    cfg = dao.get_by_user_id(current_user["id"])
    if not cfg:
        cfg = Config(user_id=current_user["id"], **data.model_dump(exclude_unset=True))
        cfg = dao.create(cfg)
    else:
        cfg = dao.update(cfg.id, data.model_dump(exclude_unset=True))
    return Result.success(ConfigOut.model_validate(cfg))


@router_v1.get("/config/{id}")
def get_config(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info("查询配置, id=%d", id)
    c = ConfigDAO(db).get_by_id(id)
    if not c:
        return Result.error("not found")
    if current_user["role"] != "admin" and c.user_id != current_user["id"]:
        return Result.error("forbidden")
    return Result.success(ConfigOut.model_validate(c))


@router_v1.post("/config")
def create_config(data: ConfigCreate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info("创建配置, user_id=%d", data.user_id)
    c = Config(**data.model_dump())
    return Result.success(ConfigOut.model_validate(ConfigDAO(db).create(c)))


@router_v1.put("/config/{id}")
def update_config(id: int, data: ConfigUpdate, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info("更新配置, id=%d", id)
    dao = ConfigDAO(db)
    c = dao.get_by_id(id)
    if not c:
        return Result.error("not found")
    if current_user["role"] != "admin" and c.user_id != current_user["id"]:
        return Result.error("forbidden")
    c = dao.update(id, data.model_dump(exclude_unset=True))
    return Result.success(ConfigOut.model_validate(c))


@router_v1.delete("/config/{id}")
def delete_config(id: int, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info("删除配置, id=%d", id)
    dao = ConfigDAO(db)
    c = dao.get_by_id(id)
    if not c:
        return Result.error("not found")
    if current_user["role"] != "admin" and c.user_id != current_user["id"]:
        return Result.error("forbidden")
    ok = dao.delete(id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post("/config/page")
def page_config(dto: PageDTO, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info("分页查询配置, page=%d size=%d", dto.page_num, dto.page_size)
    if current_user["role"] != "admin":
        return Result.error("forbidden")
    result = ConfigDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [ConfigOut.model_validate(r) for r in result.rows]
    return Result.success(result)
