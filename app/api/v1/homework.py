import logging
import time
import uuid

from fastapi import Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import get_current_user, require_role
from app.core.response import PageDTO, Result
from app.dao.task_dao import TaskDAO
from app.dao.image_dao import ImageDAO
from app.dao.question_dao import QuestionDAO
from app.dao.correction_dao import CorrectionDAO
from app.dao.block_dao import BlockDAO
from app.clients.minio import minio_client
from app.models import get_db
from app.models.image import Image
from app.models.knowledge import Knowledge
from app.models.question_chunk import QuestionChunk
from app.models.task import Task
from app.schemas import HomeworkResult, QuestionResult, BlockInfo, CorrectionInfo, ImageInfo, TaskOut, KnowledgeRef
from app.tasks.homework_tasks import homework_grading

logger = logging.getLogger(__name__)


@router_v1.post("/homework/submit", summary="提交作业", description="提交作业，返回task_id")
async def submit_homework(
    files: list[UploadFile] = File(...),
    subject: str | None = None,
    grade: str | None = None,
    current_user: dict = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    logger.info("提交作业: user_id=%s files=%d subject=%s grade=%s", current_user["id"], len(files), subject, grade)

    task_uuid = str(uuid.uuid4())

    image_urls = []
    for f in files:
        data = await f.read()
        url = f"homework/{current_user['id']}/{int(time.time())}_{f.filename}"
        ct = f"image/{f.filename.rsplit('.', 1)[-1].lower()}" if "." in f.filename else "application/octet-stream"
        minio_client.upload(url, data, content_type=ct)
        image_urls.append(url)

    task = Task(task_id=task_uuid, user_id=current_user["id"], subject=subject, grade=grade, mode="pending", status="pending")
    task = TaskDAO(db).create(task)
    for url in image_urls:
        ImageDAO(db).create(Image(task_id=task_uuid, url=url))
    db.commit()

    homework_grading.delay(task_uuid)
    logger.info("批改任务已投递: task_id=%s", task_uuid)
    return Result.success({"task_id": task_uuid})


@router_v1.post("/homework/task/page", summary="分页查询任务", description="分页查询作业任务")
def page_task(dto: PageDTO, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info("分页查询作业任务, page=%d size=%d", dto.page_num, dto.page_size)
    if current_user["role"] == "admin":
        result = TaskDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    else:
        result = TaskDAO(db).list(page=dto.page_num, page_size=dto.page_size, user_id=current_user["id"])
    result.rows = [TaskOut.model_validate(r) for r in result.rows]
    return Result.success(result)


@router_v1.get("/homework/status/{task_id}", summary="查询批改进度", description="查询作业批改进度")
def get_status(task_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info("查询任务状态, task_id=%s", task_id)
    t = TaskDAO(db).get_by_task_id(task_id)
    if not t:
        return Result.error("not found")
    if t.user_id != current_user["id"] and current_user["role"] != "admin":
        return Result.error("无权限查看")
    return Result.success({"task_id": task_id, "status": t.status})


@router_v1.get("/homework/result/{task_id}", summary="查询批改结果", description="查询批改结果，含题目/答案/得分/评语/知识引用")
def get_result(task_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info("查询批改结果, task_id=%s", task_id)

    task = TaskDAO(db).get_by_task_id(task_id)
    if not task:
        return Result.error("not found")
    if task.user_id != current_user["id"] and current_user["role"] != "admin":
        return Result.error("无权限查看")

    images = [ImageInfo(url=minio_client.get_url(img.url)) for img in ImageDAO(db).list_by_task_id(task_id)]

    questions = QuestionDAO(db).list_by_task_id(task_id)
    question_results = []
    for q in questions:
        blocks = [BlockInfo(url=minio_client.get_url(b.url), x1=b.x1, y1=b.y1, x2=b.x2, y2=b.y2)
                  for b in BlockDAO(db).list_by_question_id(q.id)]
        c = CorrectionDAO(db).get_by_question_id(q.id)
        correction = CorrectionInfo(
            score=float(c.score), result=c.result,
            comment=c.comment, analysis=c.analysis,
        ) if c else None

        chunks = db.query(QuestionChunk).filter(QuestionChunk.question_id == q.id).all()
        refs = []
        for ch in chunks:
            kn = db.query(Knowledge).filter(Knowledge.id == ch.knowledge_id).first()
            refs.append(KnowledgeRef(
                knowledge_id=ch.knowledge_id,
                title=kn.title if kn else "",
                content="",
                score=0.0,
            ))

        question_results.append(QuestionResult(
            no=q.no, question_text=q.question_text,
            student_answer=q.student_answer, question_type=q.question_type,
            create_time=str(q.create_time) if q.create_time else None,
            blocks=blocks, correction=correction, knowledge_refs=refs,
        ))

    result = HomeworkResult(
        task_id=task_id, status=task.status,
        subject=task.subject, grade=task.grade, mode=task.mode,
        create_time=str(task.create_time) if task.create_time else None,
        images=images, questions=question_results,
    )
    return Result.success(result)


@router_v1.delete("/homework/task/{task_id}", summary="删除作业", description="删除作业及相关题目/批改结果")
def delete_task(task_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    logger.info("删除作业, task_id=%s user_id=%s", task_id, current_user["id"])
    task = TaskDAO(db).get_by_task_id(task_id)
    if not task:
        return Result.error("not found")
    if task.user_id != current_user["id"] and current_user["role"] != "admin":
        return Result.error("只能删除自己的作业")

    TaskDAO(db).cascade_delete(task_id)
    db.commit()
    logger.info("作业已删除: task_id=%s", task_id)
    return Result.success()
