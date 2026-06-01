import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import require_role
from app.core.response import PageDTO, Result
from app.dao.user_dao import UserDAO
from app.models import get_db
from app.models.user import User
from app.schemas import UserCreate, UserUpdate, UserOut

logger = logging.getLogger(__name__)


@router_v1.get("/users/{id}")
def get_user(id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    logger.info("查询用户, id=%d", id)
    u = UserDAO(db).get_by_id(id)
    return Result.success(UserOut.model_validate(u)) if u else Result.error("not found")


@router_v1.post("/users")
def create_user(data: UserCreate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    logger.info("新增用户, account=%s", data.account)
    dao = UserDAO(db)
    if dao.get_by_account(data.account):
        return Result.error("account already exists")
    u = User(account=data.account, username=data.username, password=data.password, email=data.email, role=data.role)
    return Result.success(UserOut.model_validate(dao.create(u)))


@router_v1.put("/users/{id}")
def update_user(id: int, data: UserUpdate, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    logger.info("更新用户, id=%d", id)
    u = UserDAO(db).update(id, data.model_dump(exclude_unset=True))
    return Result.success(UserOut.model_validate(u)) if u else Result.error("not found")


@router_v1.delete("/users/{id}")
def delete_user(id: int, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    logger.info("删除用户, id=%d", id)
    ok = UserDAO(db).delete(id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post("/users/page")
def page_user(dto: PageDTO, db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    logger.info("分页查询用户, page=%d size=%d", dto.page_num, dto.page_size)
    result = UserDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [UserOut.model_validate(r) for r in result.rows]
    return Result.success(result)
