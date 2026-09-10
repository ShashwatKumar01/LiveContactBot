import functools
import os

from pydantic import AliasChoices, Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    master_bot_token: str = Field(alias="MASTER_BOT_TOKEN")

    mongodb_uri: str = Field(
        validation_alias=AliasChoices("MONGODB_URI", "MONGO_URI"),
    )
    mongodb_database: str = Field(alias="MONGODB_DATABASE")

    redis_url: str = Field(default="redis://localhost:6379/0", alias="REDIS_URL")
    token_encryption_key: str | None = Field(default=None, alias="TOKEN_ENCRYPTION_KEY")

    super_admin_ids: str = Field(default="", alias="SUPER_ADMIN_IDS")

    environment: str = Field(default="development", alias="ENVIRONMENT")

    webhook_host: str | None = Field(default=None, alias="WEBHOOK_HOST")
    webhook_path: str = Field(default="/webhook/master", alias="WEBHOOK_PATH")
    webhook_secret: str | None = Field(default=None, alias="WEBHOOK_SECRET")

    app_host: str = Field(default="0.0.0.0", alias="APP_HOST")
    app_port: int = Field(default=8080, alias="APP_PORT")

    broadcast_rate_limit: int = Field(default=25, alias="BROADCAST_RATE_LIMIT")
    broadcast_batch_size: int = Field(default=200, alias="BROADCAST_BATCH_SIZE")

    max_bots_free: int = Field(default=5, alias="MAX_BOTS_FREE")
    free_broadcasts_per_day: int = Field(default=-1, alias="FREE_BROADCASTS_PER_DAY")

    admin_web_password: str = Field(default="changeme", alias="ADMIN_WEB_PASSWORD")
    admin_web_secret: str = Field(default="change-this-secret-key", alias="ADMIN_WEB_SECRET")

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("super_admin_ids", mode="before")
    @classmethod
    def parse_super_admin_ids(cls, v) -> str:
        if v is None:
            return ""
        if isinstance(v, list):
            return ",".join(str(x) for x in v)
        return str(v)

    @field_validator("environment", mode="before")
    @classmethod
    def strip_environment(cls, v) -> str:
        if v is None:
            return "development"
        return str(v).split("#", 1)[0].strip().lower() or "development"

    @property
    def super_admin_id_list(self) -> list[int]:
        if not self.super_admin_ids:
            return []
        return [int(x.strip()) for x in self.super_admin_ids.split(",") if x.strip().isdigit()]

    @property
    def is_production(self) -> bool:
        return self.environment == "production"

    @model_validator(mode="after")
    def apply_railway_port(self) -> "Settings":
        port = os.getenv("PORT")
        if port and port.isdigit():
            self.app_port = int(port)
        return self


@functools.lru_cache()
def get_settings() -> Settings:
    return Settings()
