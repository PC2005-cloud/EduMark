import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import require_role
from app.core.response import PageDTO, Result
from app.dao.user_dao import UserDAO
from app.dao.task_dao import TaskDAO
from app.dao.config_dao import ConfigDAO
from app.dao.knowledge_dao import KnowledgeDAO
from app.models import get_db
from app.models.user import User
from app.models.config import Config
from app.schemas import UserCreate, UserUpdate, UserOut

logger = logging.getLogger(__name__)


@router_v1.get("/users/{id}", summary="查询用户", description="查询用户")
def get_user(id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    logger.info("查询用户, id=%d", id)
    u = UserDAO(db).get_by_id(id)
    return Result.success(UserOut.model_validate(u)) if u else Result.error("not found")


@router_v1.post("/users", summary="新增用户", description="新增用户")
def create_user(data: UserCreate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    logger.info("新增用户, account=%s", data.account)
    dao = UserDAO(db)
    if dao.get_by_account(data.account):
        return Result.error("account already exists")
    u = User(account=data.account, username=data.username, password=data.password, email=data.email, role=data.role)
    u = dao.create(u)
    db.add(Config(user_id=u.id))
    db.commit()
    return Result.success(UserOut.model_validate(u))


@router_v1.put("/users/{id}", summary="更新用户", description="更新用户")
def update_user(id: int, data: UserUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    logger.info("更新用户, id=%d", id)
    u = UserDAO(db).update(id, data.model_dump(exclude_unset=True))
    return Result.success(UserOut.model_validate(u)) if u else Result.error("not found")




@router_v1.delete("/users/{id}", summary="删除用户", description="删除用户")
def delete_user(id: int, db: Session = Depends(get_db), current_user: dict = Depends(require_role("admin"))):
    logger.info("删除用户, id=%d", id)
    if current_user["id"] == id:
        return Result.error("不能删除自己")
    u = UserDAO(db).get_by_id(id)
    if not u:
        return Result.error("not found")
    if u.account == "root":
        return Result.error("不能删除 root 账号")

    # 级联删除任务
    for task in TaskDAO(db).list(page=1, page_size=9999, user_id=id).rows:
        TaskDAO(db).cascade_delete(task.task_id)

    # 级联删除知识文档
    for kn in KnowledgeDAO(db).list(page=1, page_size=9999, user_id=id).rows:
        KnowledgeDAO(db).cascade_delete(kn.id)

    # 删除配置
    cfg = ConfigDAO(db).get_by_user_id(id)
    if cfg:
        ConfigDAO(db).delete(cfg.id)

    ok = UserDAO(db).delete(id)
    db.commit()
    logger.info("用户已删除及关联数据: id=%d", id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post("/users/page", summary="分页查询用户", description="分页查询用户")
def page_user(dto: PageDTO, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    logger.info("分页查询用户, page=%d size=%d", dto.page_num, dto.page_size)
    result = UserDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [UserOut.model_validate(r) for r in result.rows]
    return Result.success(result)
