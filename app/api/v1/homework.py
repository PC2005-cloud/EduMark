import logging
import time
import uuid

from fastapi import Depends, UploadFile, File
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import get_current_user
from app.core.response import PageDTO, Result
from app.dao.task_dao import TaskDAO
from app.dao.image_dao import ImageDAO
from app.dao.question_dao import QuestionDAO
from app.dao.correction_dao import CorrectionDAO
from app.dao.block_dao import BlockDAO
from app.clients.minio import minio_client
from app.models import get_db
from app.models.task import Task
from app.models.image import Image
from app.models.question import Question
from app.models.correction import Correction
from app.models.block import Block
from app.models.knowledge import Knowledge
from app.models.question_chunk import QuestionChunk
from app.schemas import HomeworkResult, QuestionResult, BlockInfo, CorrectionInfo, ImageInfo, TaskOut, KnowledgeRef
from app.tasks.homework_tasks import homework_grading

logger = logging.getLogger(__name__)


@router_v1.post("/homework/submit")
async def submit_homework(
    files: list[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info("提交作业: user_id=%s files=%d", current_user["id"], len(files))

    # 存 MinIO + 建 Task + 建 Image
    minio_client.ensure_bucket()
    task_uuid = str(uuid.uuid4())

    image_urls = []
    for f in files:
        data = await f.read()
        url = f"homework/{current_user['id']}/{int(time.time())}_{f.filename}"
        minio_client.upload(url, data)
        image_urls.append(url)

    task = Task(task_id=task_uuid, user_id=current_user["id"], mode="pending", status="pending")
    task = TaskDAO(db).create(task)
    for url in image_urls:
        ImageDAO(db).create(Image(task_id=task_uuid, url=url))
    db.commit()

    homework_grading.delay(task_uuid)
    logger.info("批改任务已投递: task_id=%s", task_uuid)
    return Result.success({"task_id": task_uuid})


@router_v1.post("/homework/task/page")
def page_task(dto: PageDTO, db: Session = Depends(get_db)):
    logger.info("分页查询作业任务, page=%d size=%d", dto.page_num, dto.page_size)
    result = TaskDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    result.rows = [TaskOut.model_validate(r) for r in result.rows]
    return Result.success(result)


@router_v1.get("/homework/status/{task_id}")
def get_status(task_id: str, db: Session = Depends(get_db)):
    logger.info("查询任务状态, task_id=%s", task_id)
    t = TaskDAO(db).get_by_task_id(task_id)
    return Result.success({"task_id": task_id, "status": t.status if t else "not found"})


@router_v1.get("/homework/result/{task_id}")
def get_result(task_id: str, db: Session = Depends(get_db)):
    logger.info("查询批改结果, task_id=%s", task_id)

    task = TaskDAO(db).get_by_task_id(task_id)
    if not task:
        return Result.error("not found")

    images = [ImageInfo(url=img.url) for img in ImageDAO(db).list_by_task_id(task_id)]

    questions = QuestionDAO(db).list_by_task_id(task_id)
    question_results = []
    for q in questions:
        blocks = [BlockInfo(x1=b.x1, y1=b.y1, x2=b.x2, y2=b.y2)
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
