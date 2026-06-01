import logging

from fastapi import Depends
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.response import PageDTO, Result
from app.dao.task_dao import TaskDAO
from app.models import get_db
from app.models.task import Task
from app.schemas import TaskCreate, TaskUpdate, TaskOut

logger = logging.getLogger(__name__)


@router_v1.get("/tasks/{id}")
def get_task(id: int, db: Session = Depends(get_db)):
    logger.info("查询任务, id=%d", id)
    t = TaskDAO(db).get_by_id(id)
    return Result.success(TaskOut.model_validate(t)) if t else Result.error("not found")


@router_v1.post("/tasks")
def create_task(data: TaskCreate, db: Session = Depends(get_db)):
    logger.info("创建任务, task_id=%s", data.task_id)
    t = Task(**data.model_dump())
    return Result.success(TaskOut.model_validate(TaskDAO(db).create(t)))


@router_v1.put("/tasks/{id}")
def update_task(id: int, data: TaskUpdate, db: Session = Depends(get_db)):
    logger.info("更新任务, id=%d", id)
    t = TaskDAO(db).update(id, data.model_dump(exclude_unset=True))
    return Result.success(TaskOut.model_validate(t)) if t else Result.error("not found")


@router_v1.delete("/tasks/{id}")
def delete_task(id: int, db: Session = Depends(get_db)):
    logger.info("删除任务, id=%d", id)
    ok = TaskDAO(db).delete(id)
    return Result.success() if ok else Result.error("not found")


@router_v1.post("/tasks/page")
def page_task(dto: PageDTO, db: Session = Depends(get_db)):
    logger.info("分页查询任务, page=%d size=%d", dto.page_num, dto.page_size)
    result = TaskDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [TaskOut.model_validate(r) for r in result.rows]
    return Result.success(result)
