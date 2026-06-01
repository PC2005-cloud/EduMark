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

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
