import logging
import time

from fastapi import Body, Depends, UploadFile, File, Path, Form
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import require_role
from app.core.response import PageDTO, Result, PageVO
from app.dao.knowledge_dao import KnowledgeDAO
from app.models import get_db
from app.models.knowledge import Knowledge
from app.schemas import KnowledgeOut, CurrentUser
from app.clients.minio import minio_client
from app.clients.qdrant import qdrant
from app.tasks.knowledge_tasks import knowledge_parse

logger = logging.getLogger(__name__)


@router_v1.get(
    "/knowledge/{id}",
    summary="查询知识文档",
    description="根据 ID 查询单个知识文档的详细信息。",
    tags=["知识文档"],
    response_model=Result[KnowledgeOut],
    responses={
        200: {"description": "查询成功，返回文档信息"},
    },
)
def get_knowledge(
    id: int = Path(description="知识文档 ID"),
    db: Session = Depends(get_db),
):
    logger.info("查询知识文档, id=%d", id)
    k = KnowledgeDAO(db).get_by_id(id)
    return Result.success(KnowledgeOut.model_validate(k)) if k else Result.error("not found")


@router_v1.delete(
    "/knowledge/{id}",
    summary="删除知识文档",
    description="""
删除知识文档，同步清理关联数据。

- 同时删除 MinIO 中的文件
- 同时删除 Qdrant 中的向量数据
- 只能删除自己的文档，管理员可删除任意文档
""",
    tags=["知识文档"],
    response_model=Result,
    responses={
        200: {"description": "删除成功"},
        403: {"description": "无权删除该文档"},
    },
)
def delete_knowledge(
    id: int = Path(description="知识文档 ID"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(require_role("teacher", "admin")),
):
    logger.info("删除知识文档, id=%d user_id=%s", id, current_user.id)
    dao = KnowledgeDAO(db)
    kn = dao.get_by_id(id)
    if not kn:
        return Result.error("not found")
    if kn.user_id != current_user.id and current_user.role != "admin":
        return Result.error("只能删除自己的文档")
    dao.cascade_delete(id)
    db.commit()
    logger.info("知识文档已删除: id=%d", id)
    return Result.success()


@router_v1.post(
    "/knowledge/page",
    summary="分页查询知识文档",
    description="""
分页查询知识文档列表。

- 支持排序和过滤条件
- 默认每页 10 条，最大 100 条
""",
    tags=["知识文档"],
    response_model=Result[PageVO[KnowledgeOut]],
    responses={
        200: {"description": "查询成功，返回分页数据"},
    },
)
def page_knowledge(dto: PageDTO = Body(openapi_examples={
    "默认分页": {
        "summary": "默认分页查询（第1页，每页10条）",
        "value": {"page_num": 1, "page_size": 10},
    },
    "按科目过滤": {
        "summary": "筛选数学科目的知识文档",
        "value": {"page_num": 1, "page_size": 10, "query": {"subject": "数学"}},
    },
    "按年级过滤": {
        "summary": "筛选二年级的知识文档",
        "value": {"page_num": 1, "page_size": 10, "query": {"grade": "二年级"}},
    },
}), db: Session = Depends(get_db)):
    logger.info("分页查询知识文档, page=%d size=%d", dto.page_num, dto.page_size)
    result = KnowledgeDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [KnowledgeOut.model_validate(r) for r in result.rows]
    return Result.success(result)


@router_v1.post(
    "/knowledge/upload",
    summary="上传知识文档",
    description="""
上传知识文档文件，异步解析入库。

- 支持上传 PDF、Word 等文档格式
- 上传后自动异步解析，状态由 `pending` → `parsing` → `done`
- 解析完成后内容存入向量数据库，供批改时检索
- 仅老师和管理员可上传
""",
    tags=["知识文档"],
    response_model=Result[KnowledgeOut],
    responses={
        200: {"description": "上传成功，返回文档信息，解析将在后台异步进行"},
        403: {"description": "仅老师和管理员可上传"},
    },
)
async def upload_knowledge(
    file: UploadFile = File(..., description="知识文档文件"),
    subject: str | None = Form(None, description="科目，如语文、数学"),
    grade: str | None = Form(None, description="年级，如一年级、二年级"),
    current_user: CurrentUser = Depends(require_role("teacher", "admin")),
    db: Session = Depends(get_db),
):
    logger.info("上传知识文档: filename=%s subject=%s grade=%s", file.filename, subject, grade)
    file_data = await file.read()

    object_name = f"knowledge/{current_user.id}/{int(time.time())}_{file.filename}"
    minio_client.upload(object_name, file_data)

    knowledge = Knowledge(
        user_id=current_user.id, title=file.filename, url=object_name,
        subject=subject, grade=grade, status="pending",
    )
    knowledge = KnowledgeDAO(db).create(knowledge)
    db.commit()

    knowledge_parse.delay(knowledge.id)
    logger.info("知识解析任务已投递: knowledge_id=%d", knowledge.id)
    return Result.success(KnowledgeOut.model_validate(knowledge))