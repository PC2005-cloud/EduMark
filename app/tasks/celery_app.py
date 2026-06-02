from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "edumark",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.homework_tasks",
        "app.tasks.knowledge_tasks",
    ],
)

celery_app.conf.update(
    task_track_started=True,
    task_serializer="pickle",
    result_serializer="json",
    accept_content=["pickle", "json"],
    task_time_limit=settings.CELERY_TASK_TIMEOUT,
    task_soft_time_limit=settings.CELERY_TASK_TIMEOUT - 30,
    task_max_retries=settings.CELERY_MAX_RETRIES,
    task_default_queue="edumark",
    worker_prefetch_multiplier=1,
)
