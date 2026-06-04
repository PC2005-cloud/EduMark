import logging

from fastapi import Body, Depends, Path
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import get_current_user, require_role
from app.core.response import PageDTO, Result, PageVO
from app.dao.model_dao import ModelDAO
from app.models import get_db
from app.models.model import Model
from app.schemas import ModelCreate, ModelOut

logger = logging.getLogger(__name__)


@router_v1.get(
    "/models/{id}",
    summary="查询模型",
    description="根据 ID 查询单个模型信息。",
    tags=["模型管理"],
    response_model=Result[ModelOut],
    responses={
        200: {"description": "查询成功，返回模型信息"},
    },
)
def get_model(
    id: int = Path(description="模型 ID"),
    db: Session = Depends(get_db),
    _=Depends(get_current_user),
):
    m = ModelDAO(db).get_by_id(id)
    return Result.success(ModelOut.model_validate(m)) if m else Result.error("not found")


@router_v1.post(
    "/models",
    summary="新增模型",
    description="""
添加新的 AI 模型配置，仅管理员可操作。

- **mode=1**：视觉模型，用于图片识别
- **mode=2**：语言模型，用于文本批改
""",
    tags=["模型管理"],
    response_model=Result[ModelOut],
    responses={
        200: {"description": "创建成功，返回模型信息"},
        403: {"description": "仅管理员可操作"},
    },
)
def create_model(data: ModelCreate = Body(openapi_examples={
    "新增视觉模型": {
        "summary": "添加一个视觉模型（mode=1）",
        "value": {"name": "qwen-vl-max", "mode": 1},
    },
    "新增语言模型": {
        "summary": "添加一个语言模型（mode=2）",
        "value": {"name": "qwen-max", "mode": 2},
    },
}), db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    m = Model(**data.model_dump())
    return Result.success(ModelOut.model_validate(ModelDAO(db).create(m)))


@router_v1.put(
    "/models/{id}",
    summary="更新模型",
    description="更新模型信息，仅管理员可操作。",
    tags=["模型管理"],
    response_model=Result[ModelOut],
    responses={
        200: {"description": "更新成功，返回模型信息"},
        403: {"description": "仅管理员可操作"},
    },
)
def update_model(
    id: int = Path(description="模型 ID"),
    data: ModelCreate = Body(openapi_examples={
        "更新视觉模型": {
            "summary": "更新为新的视觉模型名称",
            "value": {"name": "qwen-vl-plus", "mode": 1},
        },
        "更新语言模型": {
            "summary": "更新为新的语言模型名称",
            "value": {"name": "qwen-plus", "mode": 2},
        },
    }),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    m = ModelDAO(db).update(id, data.model_dump())
    return Result.success(ModelOut.model_validate(m)) if m else Result.error("not found")


@router_v1.delete(
    "/models/{id}",
    summary="删除模型",
    description="删除模型配置，仅管理员可操作。",
    tags=["模型管理"],
    response_model=Result,
    responses={
        200: {"description": "删除成功"},
        403: {"description": "仅管理员可操作"},
    },
)
def delete_model(
    id: int = Path(description="模型 ID"),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    ok = ModelDAO(db).delete(id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post(
    "/models/page",
    summary="分页查询模型",
    description="""
分页查询模型列表。

- 支持排序和过滤条件
- 默认每页 10 条，最大 100 条
""",
    tags=["模型管理"],
    response_model=Result[PageVO[ModelOut]],
    responses={
        200: {"description": "查询成功，返回分页数据"},
    },
)
def page_model(dto: PageDTO = Body(openapi_examples={
    "默认分页": {
        "summary": "默认分页查询（第1页，每页10条）",
        "value": {"page_num": 1, "page_size": 10},
    },
    "按类型过滤": {
        "summary": "仅查看视觉模型（mode=1）",
        "value": {"page_num": 1, "page_size": 10, "query": {"mode": 1}},
    },
    "按名称排序": {
        "summary": "按模型名称升序排列",
        "value": {
            "page_num": 1,
            "page_size": 10,
            "sort_fields": [{"field": "name", "direction": "asc"}],
        },
    },
}), db: Session = Depends(get_db), _=Depends(get_current_user)):
    result = ModelDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [ModelOut.model_validate(r) for r in result.rows]
    return Result.success(result)