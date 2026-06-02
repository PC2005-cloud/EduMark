from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    SERVER_HOST: str = "0.0.0.0"
    SERVER_PORT: int = 8000
    LOG_LEVEL: str = "info"
    CORS_ORIGINS: str = "*"

    DB_HOST: str = "localhost"
    DB_PORT: int = 7006
    DB_NAME: str = "edumark"
    DB_USER: str = "root"
    DB_PASSWORD: str = "123456"
    DB_POOL_SIZE: int = 5
    DB_MAX_OVERFLOW: int = 10

    JWT_SECRET_KEY: str = "EduMark"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 120
    JWT_REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # MinIO
    MINIO_ENDPOINT: str = "localhost:7090"
    MINIO_ACCESS_KEY: str = "minioadmin"
    MINIO_SECRET_KEY: str = "minioadmin"
    MINIO_BUCKET: str = "edumark"
    MINIO_SECURE: bool = False
    MINIO_REGION: str = "cn-east-1"

    # MinerU
    MINERU_KEY: str = ""
    MINERU_URL: str = "https://mineru.net/api/v4"

    # Aliyun OCR
    ALIYUN_ACCESS_KEY_ID: str = ""
    ALIYUN_ACCESS_KEY_SECRET: str = ""
    ALIYUN_ENDPOINT: str = "ocr-api.cn-hangzhou.aliyuncs.com"

    # Bailian
    BAILIAN_API_KEY: str = ""
    BAILIAN_API_BASE: str = "https://dashscope.aliyuncs.com/api/v1"
    BAILIAN_EMBED: str = "text-embedding-v4"

    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_HTTP_PORT: int = 7333
    QDRANT_GRPC_PORT: int = 7334
    QDRANT_COLLECTION: str = "knowledge_chunks"
    QDRANT_API_KEY: str = ""

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
