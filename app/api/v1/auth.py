import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import get_current_user
from app.core.response import Result
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.dao.user_dao import UserDAO
from app.models import get_db
from app.models.user import User
from app.models.config import Config
from app.schemas import UserCreate, UserOut, LoginSchema, RefreshSchema

logger = logging.getLogger(__name__)


@router_v1.post("/auth/register", summary="用户注册", description="用户注册")
def register(data: UserCreate, db: Session = Depends(get_db)):
    logger.info("用户注册, account=%s", data.account)
    dao = UserDAO(db)
    if dao.get_by_account(data.account):
        return Result.error("account already exists")
    user = User(account=data.account, username=data.username,
                password=hash_password(data.password), email=data.email, role=data.role)
    user = dao.create(user)
    db.add(Config(user_id=user.id))
    db.commit()
    return Result.success(UserOut.model_validate(user))


@router_v1.post("/auth/login", summary="用户登录", description="用户登录，返回JWT令牌")
def login(data: LoginSchema, db: Session = Depends(get_db)):
    logger.info("用户登录, account=%s", data.account)
    dao = UserDAO(db)
    user = dao.get_by_account(data.account)
    if not user or not verify_password(data.password, user.password):
        return Result.error("invalid account or password")
    if not user.is_active:
        return Result.error("account disabled")
    payload = {"sub": user.id, "role": user.role, "account": user.account}
    return Result.success({
        "access_token": create_access_token(payload),
        "refresh_token": create_refresh_token(payload),
        "token_type": "bearer",
    })


@router_v1.post("/auth/refresh", summary="刷新令牌", description="刷新令牌")
def refresh(data: RefreshSchema, db: Session = Depends(get_db)):
    logger.info("刷新令牌")
    token = data.token
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return Result.error("invalid refresh token")
    user = UserDAO(db).get_by_id(payload["sub"])
    if not user or not user.is_active:
        return Result.error("user not found or disabled")
    new_payload = {"sub": user.id, "role": user.role, "account": user.account}
    return Result.success({
        "access_token": create_access_token(new_payload),
        "refresh_token": create_refresh_token(new_payload),
        "token_type": "bearer",
    })


@router_v1.get("/auth/me", summary="当前用户", description="获取当前用户信息")
def me(current_user: dict = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info("查询当前用户, id=%s", current_user["id"])
    user = UserDAO(db).get_by_id(current_user["id"])
    if not user:
        return Result.error("user not found")
    return Result.success(UserOut.model_validate(user))
