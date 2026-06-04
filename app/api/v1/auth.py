import logging

from fastapi import Body, Depends, Path
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import get_current_user
from app.core.response import Result
from app.core.security import create_access_token, create_refresh_token, decode_token, hash_password, verify_password
from app.dao.user_dao import UserDAO
from app.models import get_db
from app.models.user import User
from app.models.config import Config
from app.schemas import UserCreate, UserOut, LoginSchema, RefreshSchema, TokenResponse, CurrentUser

logger = logging.getLogger(__name__)


@router_v1.post(
    "/auth/register",
    summary="用户注册",
    description="""
注册新用户账号，系统自动创建默认配置。

- **account**：登录账号，需全局唯一
- **password**：明文密码，服务端自动加密存储
- **role**：角色，可选 `student`（学生）或 `teacher`（老师）
""",
    tags=["认证管理"],
    response_model=Result[UserOut],
    responses={
        200: {"description": "注册成功，返回用户信息"},
    },
)
def register(data: UserCreate = Body(openapi_examples={
    "注册学生用户": {
        "summary": "创建一个学生账号",
        "value": {
            "account": "zhangsan",
            "username": "张三",
            "password": "123456",
            "email": "zhangsan@example.com",
            "role": "student",
        },
    },
    "注册老师用户": {
        "summary": "创建一个老师账号",
        "value": {
            "account": "teacher_wang",
            "username": "王老师",
            "password": "123456",
            "email": "wang@example.com",
            "role": "teacher",
        },
    },
}), db: Session = Depends(get_db)):
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


@router_v1.post(
    "/auth/login",
    summary="用户登录",
    description="""
使用账号密码登录，验证成功后返回 JWT 令牌。

- **access_token**：访问令牌，用于后续接口鉴权，有效期较短
- **refresh_token**：刷新令牌，用于获取新的 access_token，有效期较长
""",
    tags=["认证管理"],
    response_model=Result[TokenResponse],
    responses={
        200: {"description": "登录成功，返回 access_token 和 refresh_token"},
    },
)
def login(data: LoginSchema = Body(openapi_examples={
    "学生登录": {
        "summary": "学生账号登录",
        "value": {"account": "zhangsan", "password": "123456"},
    },
    "老师登录": {
        "summary": "老师账号登录",
        "value": {"account": "teacher_wang", "password": "123456"},
    },
}), db: Session = Depends(get_db)):
    logger.info("用户登录, account=%s", data.account)
    dao = UserDAO(db)
    user = dao.get_by_account(data.account)
    if not user or not verify_password(data.password, user.password):
        return Result.error("invalid account or password")
    if not user.is_active:
        return Result.error("account disabled")
    cu = CurrentUser(id=user.id, role=user.role, account=user.account)
    return Result.success(TokenResponse(
        access_token=create_access_token(cu),
        refresh_token=create_refresh_token(cu),
        token_type="bearer",
    ))


@router_v1.post(
    "/auth/refresh",
    summary="刷新令牌",
    description="""
使用 refresh_token 换取新的 access_token。

- 每次刷新后，旧的 refresh_token 依然有效
- 返回新的 access_token 和 refresh_token 对
""",
    tags=["认证管理"],
    response_model=Result[TokenResponse],
    responses={
        200: {"description": "刷新成功，返回新的令牌对"},
    },
)
def refresh(data: RefreshSchema = Body(openapi_examples={
    "刷新令牌": {
        "summary": "使用 refresh_token 换取新令牌",
        "value": {"token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."},
    },
}), db: Session = Depends(get_db)):
    logger.info("刷新令牌")
    token = data.token
    payload = decode_token(token)
    if not payload or payload.get("type") != "refresh":
        return Result.error("invalid refresh token")
    user = UserDAO(db).get_by_id(payload["sub"])
    if not user or not user.is_active:
        return Result.error("user not found or disabled")
    cu = CurrentUser(id=user.id, role=user.role, account=user.account)
    return Result.success(TokenResponse(
        access_token=create_access_token(cu),
        refresh_token=create_refresh_token(cu),
        token_type="bearer",
    ))


@router_v1.get(
    "/auth/me",
    summary="当前用户信息",
    description="获取当前登录用户的详细信息，需要在请求头中携带有效的 access_token。",
    tags=["认证管理"],
    response_model=Result[UserOut],
    responses={
        200: {"description": "返回当前用户信息"},
        401: {"description": "未认证或 token 无效"},
    },
)
def me(current_user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    logger.info("查询当前用户, id=%s", current_user.id)
    user = UserDAO(db).get_by_id(current_user.id)
    if not user:
        return Result.error("user not found")
    return Result.success(UserOut.model_validate(user))