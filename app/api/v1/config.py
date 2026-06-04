import logging

from fastapi import Body, Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import get_current_user
from app.core.response import Result
from app.dao.config_dao import ConfigDAO
from app.models import get_db
from app.models.config import Config
from app.models.model import Model as ModelEntity
from app.schemas import ConfigUpdate, ConfigOut, CurrentUser

logger = logging.getLogger(__name__)


@router_v1.get(
    "/config/me",
    summary="获取配置",
    description="获取当前登录用户的个性化配置。",
    tags=["配置管理"],
    response_model=Result[ConfigOut],
    responses={
        200: {"description": "查询成功，返回用户配置"},
    },
)
def get_my_config(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info("查询当前用户配置, user_id=%s", current_user.id)
    c = ConfigDAO(db).get_by_user_id(current_user.id)
    return Result.success(ConfigOut.model_validate(c)) if c else Result.error("not found")


@router_v1.put(
    "/config/me",
    summary="修改配置",
    description="""
修改当前用户的个性化配置，包含模型校验。

- **rec_mode**：`aliyun`（阿里云）或 `bailian`（百炼）
- **vl_model**：视觉模型名称，当 rec_mode 为 bailian 时必填
- **gl_model**：语言模型名称
- **enable_enhance**：是否启用增强功能
- **enable_knowledge**：是否启用知识库检索
""",
    tags=["配置管理"],
    response_model=Result[ConfigOut],
    responses={
        200: {"description": "更新成功，返回配置信息"},
    },
)
def update_my_config(data: ConfigUpdate = Body(openapi_examples={
    "阿里云模式": {
        "summary": "使用阿里云识别模式，开启增强和知识库",
        "value": {
            "rec_mode": "aliyun",
            "enable_enhance": True,
            "enable_knowledge": True,
            "gl_model": "qwen-max",
        },
    },
    "百炼模式": {
        "summary": "使用百炼识别模式，需指定视觉模型",
        "value": {
            "rec_mode": "bailian",
            "enable_enhance": True,
            "enable_knowledge": True,
            "vl_model": "qwen-vl-max",
            "gl_model": "qwen-max",
        },
    },
}), current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info("更新当前用户配置, user_id=%s", current_user.id)

    dao = ConfigDAO(db)
    cfg = dao.get_by_user_id(current_user.id)
    vals = data.model_dump(exclude_unset=True)
    rec_mode = vals.get("rec_mode", cfg.rec_mode if cfg else "aliyun")

    if rec_mode == "bailian":
        vl_model = vals.get("vl_model", cfg.vl_model if cfg else "")
        if not vl_model:
            return Result.error("视觉模式必须选择视觉模型")

    for key, mode_flag in [("vl_model", 1), ("gl_model", 2)]:
        val = vals.get(key)
        if val:
            exists = db.query(ModelEntity).filter(
                ModelEntity.name == val, ModelEntity.mode == mode_flag
            ).first()
            if not exists:
                return Result.error(f"模型 '{val}' 不存在")

    if not cfg:
        cfg = Config(user_id=current_user.id, **vals)
        cfg = dao.create(cfg)
    else:
        cfg = dao.update(cfg.id, vals)
    return Result.success(ConfigOut.model_validate(cfg))