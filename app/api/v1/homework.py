import logging
import time
import uuid

from fastapi import Body, Depends, UploadFile, File, Path, Form
from sqlalchemy.orm import Session

from app.api.v1.router import router_v1
from app.core.dependencies import get_current_user, require_role
from app.core.response import PageDTO, Result, PageVO
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
from app.schemas import HomeworkResult, QuestionResult, BlockInfo, CorrectionInfo, ImageInfo, TaskOut, KnowledgeRef, SubmitResponse, StatusResponse, CurrentUser
from app.tasks.homework_tasks import homework_grading

logger = logging.getLogger(__name__)


@router_v1.post(
    "/homework/submit",
    summary="提交作业",
    description="""
上传作业图片进行批改，异步处理。

- 支持一次上传多张图片
- 返回 task_id 用于后续查询批改进度和结果
- 仅学生角色可提交
""",
    tags=["作业管理"],
    response_model=Result[SubmitResponse],
    responses={
        200: {"description": "提交成功，返回 task_id"},
        403: {"description": "仅学生角色可提交"},
    },
)
async def submit_homework(
    files: list[UploadFile] = File(..., description="作业图片文件，支持多张"),
    subject: str | None = Form(None, description="科目，如语文、数学、英语"),
    grade: str | None = Form(None, description="年级，如一年级、二年级"),
    current_user: CurrentUser = Depends(require_role("student")),
    db: Session = Depends(get_db),
):
    logger.info("提交作业: user_id=%s files=%d subject=%s grade=%s", current_user.id, len(files), subject, grade)

    task_uuid = str(uuid.uuid4())

    image_urls = []
    for f in files:
        data = await f.read()
        url = f"homework/{current_user.id}/{int(time.time())}_{f.filename}"
        ct = f"image/{f.filename.rsplit('.', 1)[-1].lower()}" if "." in f.filename else "application/octet-stream"
        minio_client.upload(url, data, content_type=ct)
        image_urls.append(url)

    task = Task(task_id=task_uuid, user_id=current_user.id, subject=subject, grade=grade, mode="pending", status="pending")
    task = TaskDAO(db).create(task)
    for url in image_urls:
        ImageDAO(db).create(Image(task_id=task_uuid, url=url))
    db.commit()

    homework_grading.delay(task_uuid)
    logger.info("批改任务已投递: task_id=%s", task_uuid)
    return Result.success(SubmitResponse(task_id=task_uuid))


@router_v1.post(
    "/homework/task/page",
    summary="分页查询任务",
    description="""
分页查询作业任务列表。

- 学生只能查看自己的任务
- 管理员可查看所有任务
- 支持排序和过滤条件
""",
    tags=["作业管理"],
    response_model=Result[PageVO[TaskOut]],
    responses={
        200: {"description": "查询成功，返回分页数据"},
    },
)
def page_task(dto: PageDTO = Body(openapi_examples={
    "默认分页": {
        "summary": "默认分页查询（第1页，每页10条）",
        "value": {"page_num": 1, "page_size": 10},
    },
    "按状态过滤": {
        "summary": "筛选已完成的任务",
        "value": {"page_num": 1, "page_size": 10, "query": {"status": "done"}},
    },
    "按创建时间排序": {
        "summary": "按创建时间降序排列",
        "value": {
            "page_num": 1,
            "page_size": 10,
            "sort_fields": [{"field": "create_time", "direction": "desc"}],
        },
    },
}), db: Session = Depends(get_db), current_user: CurrentUser = Depends(get_current_user)):
    logger.info("分页查询作业任务, page=%d size=%d", dto.page_num, dto.page_size)
    if current_user.role == "admin":
        result = TaskDAO(db).list(page=dto.page_num, page_size=dto.page_size)
    else:
        result = TaskDAO(db).list(page=dto.page_num, page_size=dto.page_size, user_id=current_user.id)
    result.rows = [TaskOut.model_validate(r) for r in result.rows]
    return Result.success(result)


@router_v1.get(
    "/homework/status/{task_id}",
    summary="查询批改进度",
    description="""
查询作业批改的当前状态。

- 只能查看自己的任务或管理员可查看所有
- 状态值：`pending`（待处理）、`processing`（处理中）、`done`（已完成）
""",
    tags=["作业管理"],
    response_model=Result[StatusResponse],
    responses={
        200: {"description": "查询成功，返回任务状态"},
        403: {"description": "无权查看该任务"},
    },
)
def get_status(
    task_id: str = Path(description="任务唯一标识"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    logger.info("查询任务状态, task_id=%s", task_id)
    t = TaskDAO(db).get_by_task_id(task_id)
    if not t:
        return Result.error("not found")
    if t.user_id != current_user.id and current_user.role != "admin":
        return Result.error("无权限查看")
    return Result.success(StatusResponse(task_id=task_id, status=t.status))


@router_v1.get(
    "/homework/result/{task_id}",
    summary="查询批改结果",
    description="""
获取完整的批改结果，包含：

- 原始作业图片（带访问链接）
- 每道题目的识别文本、学生答案
- 每道题目的裁切区域坐标
- AI 批改得分、评语、错因分析
- 关联的知识库引用
""",
    tags=["作业管理"],
    response_model=Result[HomeworkResult],
    responses={
        200: {"description": "查询成功，返回完整批改结果"},
        403: {"description": "无权查看该任务"},
    },
)
def get_result(
    task_id: str = Path(description="任务唯一标识"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    logger.info("查询批改结果, task_id=%s", task_id)

    task = TaskDAO(db).get_by_task_id(task_id)
    if not task:
        return Result.error("not found")
    if task.user_id != current_user.id and current_user.role != "admin":
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


@router_v1.delete(
    "/homework/task/{task_id}",
    summary="删除作业",
    description="""
删除作业及相关题目、批改结果。

- 只能删除自己的作业
- 管理员可删除任意作业
- 级联删除所有关联数据
""",
    tags=["作业管理"],
    response_model=Result,
    responses={
        200: {"description": "删除成功"},
        403: {"description": "无权删除该作业"},
    },
)
def delete_task(
    task_id: str = Path(description="任务唯一标识"),
    db: Session = Depends(get_db),
    current_user: CurrentUser = Depends(get_current_user),
):
    logger.info("删除作业, task_id=%s user_id=%s", task_id, current_user.id)
    task = TaskDAO(db).get_by_task_id(task_id)
    if not task:
        return Result.error("not found")
    if task.user_id != current_user.id and current_user.role != "admin":
        return Result.error("只能删除自己的作业")

    TaskDAO(db).cascade_delete(task_id)
    db.commit()
    logger.info("作业已删除: task_id=%s", task_id)
    return Result.success()