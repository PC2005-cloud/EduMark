import logging
import time

from fastapi import Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import require_role
from app.core.response import PageDTO, Result
from app.dao.knowledge_dao import KnowledgeDAO
from app.models import get_db
from app.models.knowledge import Knowledge
from app.schemas import KnowledgeOut
from app.clients.minio import minio_client
from app.clients.qdrant import qdrant
from app.tasks.knowledge_tasks import knowledge_parse

logger = logging.getLogger(__name__)


@router_v1.get("/knowledge/{id}", summary="查询知识文档", description="查询知识文档")
def get_knowledge(id: int, db: Session = Depends(get_db)):
    logger.info("查询知识文档, id=%d", id)
    k = KnowledgeDAO(db).get_by_id(id)
    return Result.success(KnowledgeOut.model_validate(k)) if k else Result.error("not found")


@router_v1.delete("/knowledge/{id}", summary="删除知识文档", description="删除知识文档，同步清理MinIO和Qdrant")
def delete_knowledge(id: int, db: Session = Depends(get_db), current_user: dict = Depends(require_role("teacher", "admin"))):
    logger.info("删除知识文档, id=%d user_id=%s", id, current_user["id"])
    dao = KnowledgeDAO(db)
    kn = dao.get_by_id(id)
    if not kn:
        return Result.error("not found")
    if kn.user_id != current_user["id"] and current_user["role"] != "admin":
        return Result.error("只能删除自己的文档")
    dao.cascade_delete(id)
    db.commit()
    logger.info("知识文档已删除: id=%d", id)
    return Result.success()


@router_v1.post("/knowledge/page", summary="分页知识文档", description="分页查询知识文档")
def page_knowledge(dto: PageDTO, db: Session = Depends(get_db)):
    logger.info("分页查询知识文档, page=%d size=%d", dto.page_num, dto.page_size)
    result = KnowledgeDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [KnowledgeOut.model_validate(r) for r in result.rows]
    return Result.success(result)


@router_v1.post("/knowledge/upload", summary="上传知识文档", description="上传知识文档，异步解析")
async def upload_knowledge(
    file: UploadFile = File(...),
    subject: str | None = None,
    grade: str | None = None,
    current_user: dict = Depends(require_role("teacher", "admin")),
    db: Session = Depends(get_db),
):
    logger.info("上传知识文档: filename=%s subject=%s grade=%s", file.filename, subject, grade)
    file_data = await file.read()

    object_name = f"knowledge/{current_user['id']}/{int(time.time())}_{file.filename}"
    minio_client.upload(object_name, file_data)

    knowledge = Knowledge(
        user_id=current_user["id"], title=file.filename, url=object_name,
        subject=subject, grade=grade, status="pending",
    )
    knowledge = KnowledgeDAO(db).create(knowledge)
    db.commit()

    knowledge_parse.delay(knowledge.id)
    logger.info("知识解析任务已投递: knowledge_id=%d", knowledge.id)
    return Result.success(KnowledgeOut.model_validate(knowledge))
