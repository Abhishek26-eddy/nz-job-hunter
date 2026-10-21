from functools import lru_cache
from typing import Any, List, Optional

from pydantic import Field, PostgresDsn, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    environment: str = "development"
    debug: bool = False
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    project_name: str = "Europe Job Agent"
    frontend_url: str = "http://localhost:3001"

    database_url: PostgresDsn
    database_url_sync: PostgresDsn

    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str = "redis://localhost:6379/1"
    celery_result_backend: str = "redis://localhost:6379/2"

    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-2.0-flash"

    # Local AI pipeline
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_fallback_model: str = "sentence-transformers/all-MiniLM-L6-v2"
    embedding_device: str = "cpu"
    vector_backend: str = "numpy"  # "numpy" or "pgvector"
    top_jobs_for_ollama: int = 25
    ollama_url: str = "http://host.docker.internal:11434"
    ollama_model: str = "qwen2.5:7b"
    ollama_fallback_model: str = "llama3.1:8b"

    aws_region: str = "eu-west-1"
    aws_access_key_id: Optional[str] = None
    aws_secret_access_key: Optional[str] = None
    s3_bucket_name: Optional[str] = None

    slack_webhook_url: Optional[str] = None
    telegram_bot_token: Optional[str] = None
    telegram_chat_id: Optional[str] = None
    discord_webhook_url: Optional[str] = None
    sentry_dsn: Optional[str] = None

    crawler_interval_hours: int = 4
    max_concurrent_crawls: int = 5
    user_agent: str = "EuropeJobAgent/1.0"

    @field_validator("database_url", "database_url_sync", mode="before")
    @classmethod
    def assemble_db_urls(cls, v: Any) -> Any:
        if isinstance(v, str):
            return v
        return v

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
