"""
Central configuration module for SwarmEnterprise v2.

Reads all environment variables via pydantic Settings, validates required vars
on startup, and provides typed access grouped by subsystem.

Usage:
    from backend.config import settings
    print(settings.jwt.secret_key)
"""

import logging
from functools import lru_cache
from typing import Optional

from pydantic import ConfigDict, Field, field_validator
from pydantic_settings import BaseSettings  # pydantic v2 — requires pydantic-settings

logger = logging.getLogger("SwarmConfig")


class DatabaseSettings(BaseSettings):
    model_config = ConfigDict(env_prefix="", extra="ignore")

    url: str = Field(default="sqlite:///./swarm.db", json_schema_extra={"env": "DATABASE_URL"})


class RedisSettings(BaseSettings):
    model_config = ConfigDict(env_prefix="", extra="ignore")

    host: str = Field(default="localhost", json_schema_extra={"env": "REDIS_HOST"})
    port: int = Field(default=6379, json_schema_extra={"env": "REDIS_PORT"})
    url: Optional[str] = Field(default=None, json_schema_extra={"env": "REDIS_URL"})
    queue_key: str = Field(
        default="swarm_outreach_queue", json_schema_extra={"env": "REDIS_QUEUE_KEY"}
    )


class StripeSettings(BaseSettings):
    model_config = ConfigDict(env_prefix="", extra="ignore")

    api_key: str = Field(default="sk_test_placeholder", json_schema_extra={"env": "STRIPE_API_KEY"})
    webhook_secret: str = Field(
        default="whsec_placeholder", json_schema_extra={"env": "STRIPE_WEBHOOK_SECRET"}
    )


class SmtpSettings(BaseSettings):
    model_config = ConfigDict(env_prefix="", extra="ignore")

    host: Optional[str] = Field(default=None, json_schema_extra={"env": "SMTP_HOST"})
    port: int = Field(default=587, json_schema_extra={"env": "SMTP_PORT"})
    username: Optional[str] = Field(default=None, json_schema_extra={"env": "SMTP_USERNAME"})
    password: Optional[str] = Field(default=None, json_schema_extra={"env": "SMTP_PASSWORD"})
    from_email: str = Field(
        default="noreply@realms2riches.tech", json_schema_extra={"env": "SMTP_FROM_EMAIL"}
    )


class JwtSettings(BaseSettings):
    model_config = ConfigDict(env_prefix="", extra="ignore")

    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        json_schema_extra={"env": "JWT_SECRET_KEY"},
    )
    access_token_expire_minutes: int = Field(
        default=15, json_schema_extra={"env": "ACCESS_TOKEN_EXPIRE_MINUTES"}
    )
    refresh_token_expire_days: int = Field(
        default=7, json_schema_extra={"env": "REFRESH_TOKEN_EXPIRE_DAYS"}
    )

    @field_validator("secret_key")
    @classmethod
    def secret_key_must_not_be_default_in_production(cls, v: str) -> str:
        import os

        if (
            os.getenv("DEPLOY_PROFILE", "local") != "local"
            and v == "your-secret-key-change-in-production"
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be set to a strong secret in non-local deployments"
            )
        return v


class LlmSettings(BaseSettings):
    model_config = ConfigDict(env_prefix="", extra="ignore")

    ollama_url: str = Field(
        default="http://localhost:11434", json_schema_extra={"env": "OLLAMA_URL"}
    )
    ollama_model: str = Field(default="llama3.2:3b", json_schema_extra={"env": "OLLAMA_MODEL"})
    ollama_temperature: float = Field(default=0.1, json_schema_extra={"env": "OLLAMA_TEMPERATURE"})
    embedding_model: str = Field(
        default="nomic-embed-text:latest", json_schema_extra={"env": "EMBEDDING_MODEL"}
    )


class DeploymentSettings(BaseSettings):
    model_config = ConfigDict(env_prefix="", extra="ignore")

    ssh_host: Optional[str] = Field(default=None, json_schema_extra={"env": "DEPLOY_SSH_HOST"})
    ssh_user: str = Field(default="ubuntu", json_schema_extra={"env": "DEPLOY_SSH_USER"})
    ssh_key_path: str = Field(
        default="~/.ssh/id_rsa", json_schema_extra={"env": "DEPLOY_SSH_KEY_PATH"}
    )
    docker_image: str = Field(
        default="nginx:alpine", json_schema_extra={"env": "DEPLOY_DOCKER_IMAGE"}
    )
    cloudflare_api_token: Optional[str] = Field(
        default=None, json_schema_extra={"env": "CLOUDFLARE_API_TOKEN"}
    )
    cloudflare_zone_id: Optional[str] = Field(
        default=None, json_schema_extra={"env": "CLOUDFLARE_ZONE_ID"}
    )
    tech_domain: str = Field(default="realms2riches.tech", json_schema_extra={"env": "TECH_DOMAIN"})
    hosts_file_path: str = Field(default="/etc/hosts", json_schema_extra={"env": "HOSTS_FILE_PATH"})


class Settings(BaseSettings):
    """Aggregated settings object — import this in application code."""

    model_config = ConfigDict(env_prefix="", extra="ignore")

    database: DatabaseSettings = Field(default_factory=DatabaseSettings)
    redis: RedisSettings = Field(default_factory=RedisSettings)
    stripe: StripeSettings = Field(default_factory=StripeSettings)
    smtp: SmtpSettings = Field(default_factory=SmtpSettings)
    jwt: JwtSettings = Field(default_factory=JwtSettings)
    llm: LlmSettings = Field(default_factory=LlmSettings)
    deployment: DeploymentSettings = Field(default_factory=DeploymentSettings)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Module-level convenience alias
settings = get_settings()
