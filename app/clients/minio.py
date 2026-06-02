import logging
from io import BytesIO

from minio import Minio
from minio.error import S3Error

from app.core.config import settings

logger = logging.getLogger(__name__)


class MinioClient:
    def __init__(self):
        self._client = Minio(
            settings.MINIO_ENDPOINT,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
            region=settings.MINIO_REGION,
        )
        self._bucket = settings.MINIO_BUCKET
        logger.info("MinIO 客户端初始化: endpoint=%s bucket=%s", settings.MINIO_ENDPOINT, self._bucket)

    def ensure_bucket(self):
        logger.info("检查存储桶: %s", self._bucket)
        if not self._client.bucket_exists(self._bucket):
            self._client.make_bucket(self._bucket)
            logger.info("创建存储桶: %s", self._bucket)
        else:
            logger.debug("存储桶已存在: %s", self._bucket)

    def exists(self, object_name: str) -> bool:
        logger.debug("检查文件: %s", object_name)
        try:
            self._client.stat_object(self._bucket, object_name)
            logger.debug("文件存在: %s", object_name)
            return True
        except S3Error:
            logger.debug("文件不存在: %s", object_name)
            return False

    def upload(self, object_name: str, data: bytes, content_type: str = "application/octet-stream"):
        logger.info("上传文件: %s size=%d content_type=%s", object_name, len(data), content_type)
        self._client.put_object(
            self._bucket, object_name,
            BytesIO(data), len(data),
            content_type=content_type,
        )
        logger.info("上传成功: %s", object_name)

    def download(self, object_name: str) -> bytes:
        logger.info("下载文件: %s", object_name)
        if not self.exists(object_name):
            logger.error("文件不存在: %s", object_name)
            raise FileNotFoundError(f"文件不存在: {object_name}")
        response = self._client.get_object(self._bucket, object_name)
        data = response.read()
        response.close()
        logger.info("下载成功: %s size=%d", object_name, len(data))
        return data

    def delete(self, object_name: str):
        logger.info("删除文件: %s", object_name)
        if not self.exists(object_name):
            logger.error("文件不存在: %s", object_name)
            raise FileNotFoundError(f"文件不存在: {object_name}")
        self._client.remove_object(self._bucket, object_name)
        logger.info("删除成功: %s", object_name)

    def get_url(self, object_name: str) -> str:
        url = f"http://{settings.MINIO_ENDPOINT}/{self._bucket}/{object_name}"
        logger.debug("获取文件URL: %s", url)
        return url


minio_client = MinioClient()
