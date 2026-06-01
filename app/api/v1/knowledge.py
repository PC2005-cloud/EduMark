import logging

from fastapi import Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import require_role
from app.core.response import PageDTO, Result
from app.dao.knowledge_dao import KnowledgeDAO
from app.models import get_db
from app.models.knowledge import Knowledge
from app.schemas import KnowledgeCreate, KnowledgeUpdate, KnowledgeOut

logger = logging.getLogger(__name__)


@router_v1.get("/knowledge/{id}")
def get_knowledge(id: int, db: Session = Depends(get_db)):
    logger.info("查询知识文档, id=%d", id)
    k = KnowledgeDAO(db).get_by_id(id)
    return Result.success(KnowledgeOut.model_validate(k)) if k else Result.error("not found")


@router_v1.post("/knowledge")
def create_knowledge(data: KnowledgeCreate, db: Session = Depends(get_db)):
    logger.info("创建知识文档, title=%s", data.title)
    k = Knowledge(**data.model_dump())
    return Result.success(KnowledgeOut.model_validate(KnowledgeDAO(db).create(k)))


@router_v1.put("/knowledge/{id}")
def update_knowledge(id: int, data: KnowledgeUpdate, db: Session = Depends(get_db)):
    logger.info("更新知识文档, id=%d", id)
    k = KnowledgeDAO(db).update(id, data.model_dump(exclude_unset=True))
    return Result.success(KnowledgeOut.model_validate(k)) if k else Result.error("not found")


@router_v1.delete("/knowledge/{id}")
def delete_knowledge(id: int, db: Session = Depends(get_db)):
    logger.info("删除知识文档, id=%d", id)
    ok = KnowledgeDAO(db).delete(id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post("/knowledge/page")
def page_knowledge(dto: PageDTO, db: Session = Depends(get_db)):
    logger.info("分页查询知识文档, page=%d size=%d", dto.page_num, dto.page_size)
    result = KnowledgeDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [KnowledgeOut.model_validate(r) for r in result.rows]
    return Result.success(result)


@router_v1.post("/knowledge/upload")
def upload_knowledge(
    file: UploadFile = File(...),
    subject: str | None = None,
    grade: str | None = None,
    _=Depends(require_role("teacher", "admin")),
    db: Session = Depends(get_db),
):
    logger.info("上传知识文档, filename=%s subject=%s grade=%s", file.filename, subject, grade)
    return Result.success({"knowledge_id": None})


@router_v1.post("/knowledge/search")
def search_knowledge(query: str, top_k: int = 5, db: Session = Depends(get_db)):
    logger.info("搜索知识库, query=%s top_k=%d", query, top_k)
    return Result.success([])


@router_v1.delete("/knowledge/clear")
def clear_knowledge(_=Depends(require_role("admin")), db: Session = Depends(get_db)):
    logger.info("清空知识库")
    return Result.success()
