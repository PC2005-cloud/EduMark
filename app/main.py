import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1 import router_v1
from app.core.config import settings
from app.core.exceptions import AppException
from app.core.response import Result

# 配置根日志输出到控制台
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(name)s %(message)s'
)


logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("正在预热各服务连接...")
    try:
        from app.clients.minio import minio_client
        minio_client.ensure_bucket()
        logger.info("MinIO 连接就绪")
    except Exception as e:
        logger.warning("MinIO 预热失败: %s", e)

    try:
        from app.clients.qdrant import qdrant
        qdrant.ensure_collection()
        logger.info("Qdrant 连接就绪")
    except Exception as e:
        logger.warning("Qdrant 预热失败: %s", e)

    try:
        from app.models import engine
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        logger.info("MySQL 连接就绪")
    except Exception as e:
        logger.warning("MySQL 预热失败: %s", e)

    yield


app = FastAPI(
    title="EduMark",
    description="基于大模型的中小学作业批改系统",
    version="0.1.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(router_v1)


# ==================== 全局异常处理 ====================

@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    logger.warning("业务异常: %s path=%s", exc.message, request.url.path)
    return JSONResponse(
        status_code=200,
        content=Result.error(exc.message).model_dump(),
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    messages = [f"{e['loc'][-1]}: {e['msg']}" for e in exc.errors()]
    msg = "; ".join(messages)
    logger.warning("参数校验失败: %s path=%s", msg, request.url.path)
    return JSONResponse(
        status_code=200,
        content=Result.error(msg).model_dump(),
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("未处理异常: %s path=%s", exc, request.url.path, exc_info=True)
    return JSONResponse(
        status_code=500,
        content=Result.error("服务器内部错误").model_dump(),
    )
