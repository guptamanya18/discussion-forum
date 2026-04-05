from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file="../../../.env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    secret_key: str = Field(alias="SECRET_KEY")
    algorithm: str = Field(alias="ALGORITHM")
    access_token_expire_minutes: int = Field(alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    database_url: str = Field(alias="DATABASE_URL")
    kafka_bootstrap_servers: str = Field(default="kafka:9092", alias="KAFKA_BOOTSTRAP_SERVERS")


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
