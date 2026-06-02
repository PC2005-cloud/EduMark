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


@router_v1.get("/knowledge/{id}")
def get_knowledge(id: int, db: Session = Depends(get_db)):
    logger.info("查询知识文档, id=%d", id)
    k = KnowledgeDAO(db).get_by_id(id)
    return Result.success(KnowledgeOut.model_validate(k)) if k else Result.error("not found")


@router_v1.delete("/knowledge/{id}")
def delete_knowledge(id: int, db: Session = Depends(get_db)):
    logger.info("删除知识文档, id=%d", id)
    dao = KnowledgeDAO(db)
    kn = dao.get_by_id(id)
    if not kn:
        return Result.error("not found")
    if kn.url:
        try:
            minio_client.delete(kn.url)
        except Exception as e:
            logger.warning("MinIO 删除失败: %s", e)
    try:
        qdrant.delete({"document_id": id})
    except Exception as e:
        logger.warning("Qdrant 删除失败: %s", e)
    dao.delete(id)
    logger.info("知识文档已删除: id=%d", id)
    return Result.success()


@router_v1.post("/knowledge/page")
def page_knowledge(dto: PageDTO, db: Session = Depends(get_db)):
    logger.info("分页查询知识文档, page=%d size=%d", dto.page_num, dto.page_size)
    result = KnowledgeDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [KnowledgeOut.model_validate(r) for r in result.rows]
    return Result.success(result)


@router_v1.post("/knowledge/upload")
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
    minio_client.ensure_bucket()
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
