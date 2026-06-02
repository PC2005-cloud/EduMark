import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import require_role
from app.core.response import PageDTO, Result
from app.dao.model_dao import ModelDAO
from app.models import get_db
from app.models.model import Model
from app.schemas import ModelCreate, ModelOut

logger = logging.getLogger(__name__)


@router_v1.get("/models/{id}", summary="查询模型", description="查询模型")
def get_model(id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    m = ModelDAO(db).get_by_id(id)
    return Result.success(ModelOut.model_validate(m)) if m else Result.error("not found")


@router_v1.post("/models", summary="新增模型", description="新增模型")
def create_model(data: ModelCreate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    m = Model(**data.model_dump())
    return Result.success(ModelOut.model_validate(ModelDAO(db).create(m)))


@router_v1.put("/models/{id}", summary="更新模型", description="更新模型")
def update_model(id: int, data: ModelCreate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    m = ModelDAO(db).update(id, data.model_dump())
    return Result.success(ModelOut.model_validate(m)) if m else Result.error("not found")


@router_v1.delete("/models/{id}", summary="删除模型", description="删除模型")
def delete_model(id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    ok = ModelDAO(db).delete(id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post("/models/page", summary="分页查询模型", description="分页查询模型")
def page_model(dto: PageDTO, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    result = ModelDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [ModelOut.model_validate(r) for r in result.rows]
    return Result.success(result)
