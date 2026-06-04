import logging

from fastapi import Body, Depends, Path
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import require_role
from app.core.response import PageDTO, Result, PageVO
from app.dao.user_dao import UserDAO
from app.dao.task_dao import TaskDAO
from app.dao.config_dao import ConfigDAO
from app.dao.knowledge_dao import KnowledgeDAO
from app.models import get_db
from app.models.user import User
from app.models.config import Config
from app.schemas import UserCreate, UserUpdate, UserOut, CurrentUser

logger = logging.getLogger(__name__)


@router_v1.get(
    "/users/{id}",
    summary="查询用户",
    description="根据用户 ID 查询用户详细信息，仅管理员可操作。",
    tags=["用户管理"],
    response_model=Result[UserOut],
    responses={
        200: {"description": "查询成功，返回用户信息"},
        403: {"description": "无管理员权限"},
    },
)
def get_user(
    id: int = Path(description="用户 ID"),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    logger.info("查询用户, id=%d", id)
    u = UserDAO(db).get_by_id(id)
    return Result.success(UserOut.model_validate(u)) if u else Result.error("not found")


@router_v1.post(
    "/users",
    summary="新增用户",
    description="""
创建新用户，仅管理员可操作。

- 账号需全局唯一，重复创建会报错
- 创建用户时会自动初始化默认配置
""",
    tags=["用户管理"],
    response_model=Result[UserOut],
    responses={
        200: {"description": "创建成功，返回用户信息"},
        403: {"description": "无管理员权限"},
    },
)
def create_user(data: UserCreate = Body(openapi_examples={
    "创建学生用户": {
        "summary": "创建一个学生账号",
        "value": {
            "account": "zhangsan",
            "username": "张三",
            "password": "123456",
            "email": "zhangsan@example.com",
            "role": "student",
        },
    },
    "创建老师用户": {
        "summary": "创建一个老师账号",
        "value": {
            "account": "teacher_wang",
            "username": "王老师",
            "password": "123456",
            "email": "wang@example.com",
            "role": "teacher",
        },
    },
}), db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    logger.info("新增用户, account=%s", data.account)
    dao = UserDAO(db)
    if dao.get_by_account(data.account):
        return Result.error("account already exists")
    u = User(account=data.account, username=data.username, password=data.password, email=data.email, role=data.role)
    u = dao.create(u)
    db.add(Config(user_id=u.id))
    db.commit()
    return Result.success(UserOut.model_validate(u))


@router_v1.put(
    "/users/{id}",
    summary="更新用户",
    description="更新用户信息，仅管理员可操作。只需传入需要修改的字段。",
    tags=["用户管理"],
    response_model=Result[UserOut],
    responses={
        200: {"description": "更新成功，返回用户信息"},
        403: {"description": "无管理员权限"},
    },
)
def update_user(
    id: int = Path(description="用户 ID"),
    data: UserUpdate = Body(openapi_examples={
        "更新昵称": {
            "summary": "修改用户昵称",
            "value": {"username": "张三（新昵称）"},
        },
        "更新邮箱": {
            "summary": "修改用户邮箱",
            "value": {"email": "newemail@example.com"},
        },
        "禁用用户": {
            "summary": "禁用用户账号",
            "value": {"is_active": False},
        },
    }),
    db: Session = Depends(get_db),
    _=Depends(require_role("admin")),
):
    logger.info("更新用户, id=%d", id)
    u = UserDAO(db).update(id, data.model_dump(exclude_unset=True))
    return Result.success(UserOut.model_validate(u)) if u else Result.error("not found")


@router_v1.delete(
    "/users/{id}",
    summary="删除用户",
    description="""
删除用户，仅管理员可操作。执行以下限制：

- 不能删除自己
- 不能删除 root 账号
- 删除时会级联删除该用户的所有作业、知识文档和配置
""",
    tags=["用户管理"],
    response_model=Result,
    responses={
        200: {"description": "删除成功"},
        403: {"description": "无管理员权限"},
    },
)
def delete_user(
    id: int = Path(description="用户 ID"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("admin")),
):
    logger.info("删除用户, id=%d", id)
    if current_user.id == id:
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


@router_v1.post(
    "/users/page",
    summary="分页查询用户",
    description="""
分页查询用户列表，仅管理员可操作。

- 支持排序和过滤条件
- 默认每页 10 条，最大 100 条
""",
    tags=["用户管理"],
    response_model=Result[PageVO[UserOut]],
    responses={
        200: {"description": "查询成功，返回分页数据"},
        403: {"description": "无管理员权限"},
    },
)
def page_user(dto: PageDTO = Body(openapi_examples={
    "默认分页": {
        "summary": "默认分页查询（第1页，每页10条）",
        "value": {"page_num": 1, "page_size": 10},
    },
    "按角色过滤": {
        "summary": "筛选学生用户",
        "value": {"page_num": 1, "page_size": 10, "query": {"role": "student"}},
    },
    "按账号排序": {
        "summary": "按账号升序排列",
        "value": {
            "page_num": 1,
            "page_size": 10,
            "sort_fields": [{"field": "account", "direction": "asc"}],
        },
    },
}), db: Session = Depends(get_db), _=Depends(require_role("admin"))):
    logger.info("分页查询用户, page=%d size=%d", dto.page_num, dto.page_size)
    result = UserDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [UserOut.model_validate(r) for r in result.rows]
    return Result.success(result)