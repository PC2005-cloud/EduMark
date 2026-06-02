from app.tasks.celery_app import celery_app


@celery_app.task(bind=True, max_retries=3, serializer="pickle")
def homework_grading(self, file_data: bytes, filename: str,
                     user_id: int) -> dict:
    """异步批改作业

    入参:
        file_data: 图片字节 (pickle 序列化)
        filename: 文件名
        user_id: 提交作业的用户 ID（从 config 读取识别模式）

    流程:
        存 MinIO → 建 Task 记录 → 读 config → 预处理 → OCR 识别 → 保存题目

    返回:
        {"task_id": str, "questions_count": int, "status": str}
    """
    raise NotImplementedError
