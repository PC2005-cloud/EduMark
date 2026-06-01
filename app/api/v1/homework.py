import logging

from fastapi import Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import get_current_user
from app.core.response import Result
from app.dao.task_dao import TaskDAO
from app.models import get_db

logger = logging.getLogger(__name__)


@router_v1.post("/homework/submit")
async def submit_homework(
    files: list[UploadFile] = File(...),
    mode: str = "aliyun",
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info("提交作业, user_id=%s mode=%s files=%d", current_user["id"], mode, len(files))
    return Result.success({"task_id": None})


@router_v1.get("/homework/status/{task_id}")
def get_status(task_id: str, db: Session = Depends(get_db)):
    logger.info("查询任务状态, task_id=%s", task_id)
    t = TaskDAO(db).get_by_task_id(task_id)
    return Result.success({"task_id": task_id, "status": t.status if t else "not found"})


@router_v1.get("/homework/result/{task_id}")
def get_result(task_id: str, db: Session = Depends(get_db)):
    logger.info("查询批改结果, task_id=%s", task_id)
    return Result.success({"task_id": task_id})
