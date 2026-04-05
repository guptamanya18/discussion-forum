from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    secret_key: str = Field(alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    user_service_url: str = Field(default="http://localhost:8002", alias="USER_SERVICE_URL")
    thread_service_url: str = Field(default="http://localhost:8003", alias="THREAD_SERVICE_URL")
    comment_service_url: str = Field(default="http://localhost:8005", alias="COMMENT_SERVICE_URL")
    community_service_url: str = Field(default="http://localhost:8006", alias="COMMUNITY_SERVICE_URL")
    notification_service_url: str = Field(default="http://localhost:8007", alias="NOTIFICATION_SERVICE_URL")
    redis_url: str = Field(default="redis://localhost:6379", alias="REDIS_URL")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
