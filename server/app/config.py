from functools import lru_cache
from typing import Literal

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: SecretStr = Field(
        ...,
        description="PostgreSQL connection string with pgvector support",
    )

    # Redis
    redis_url: SecretStr = Field(
        ...,
        description="Redis connection string (Upstash)",
    )

    # JWT Authentication
    secret_key: SecretStr = Field(
        ...,
        description="Secret key for JWT token signing",
    )
    algorithm: str = Field(
        default="HS256",
        description="JWT signing algorithm",
    )
    access_token_expire_minutes: int = Field(
        default=30,
        description="Access token expiration time in minutes",
    )
    refresh_token_expire_days: int = Field(
        default=7,
        description="Refresh token expiration time in days",
    )

    # Monitoring
    sentry_dsn: SecretStr | None = Field(
        default=None,
        description="Sentry DSN for error tracking (optional)",
    )

    # Environment
    environment: Literal["local", "staging", "production"] = Field(
        default="local",
        description="Deployment environment",
    )

    # Jina AI Embeddings
    jina_api_key: SecretStr = Field(
        ...,
        description="Jina AI API key for embedding generation",
    )
    jina_embedding_model: str = Field(
        default="jina-embeddings-v3",
        description="Jina embedding model to use",
    )
    embedding_batch_size: int = Field(
        default=100,
        description="Batch size for embedding generation",
    )

    # Short-term memory
    short_term_max_tokens: int = Field(
        default=4000,
        description="Max token budget for short-term sliding window",
    )
    short_term_auto_checkpoint_threshold: float = Field(
        default=0.8,
        description="Threshold ratio to trigger automatic short-term checkpointing",
    )

    # Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
    )

    # API Configuration
    api_v1_prefix: str = Field(
        default="/api/v1",
        description="API v1 route prefix",
    )

    @field_validator("short_term_auto_checkpoint_threshold")
    @classmethod
    def validate_short_term_auto_checkpoint_threshold(cls, v: float) -> float:
        """Validate auto-checkpoint threshold is in the open interval (0, 1]."""
        if v <= 0 or v > 1:
            raise ValueError("short_term_auto_checkpoint_threshold must be in (0, 1]")
        return v

    @field_validator("log_level")
    @classmethod
    def validate_log_level(cls, v: str) -> str:
        """Validate log level is a valid option."""
        valid_levels = {"DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"}
        v_upper = v.upper()
        if v_upper not in valid_levels:
            raise ValueError(f"log_level must be one of {valid_levels}")
        return v_upper

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == "production"

    @property
    def is_local(self) -> bool:
        """Check if running in local environment."""
        return self.environment == "local"


@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.
    
    Settings are loaded once and cached for the application lifetime.
    """
    return Settings()


def get_test_settings() -> Settings:
    """
    Get settings for testing with overridden database URL.
    
    Uses a separate test database to avoid polluting production data.
    """
    settings = get_settings()
    
    # Override database URL for testing
    test_db_url = settings.database_url.get_secret_value().replace(
        "/remembr", "/remembr_test"
    )
    
    return Settings(
        database_url=SecretStr(test_db_url),
        redis_url=settings.redis_url,
        secret_key=settings.secret_key,
        jina_api_key=settings.jina_api_key,
        environment="local",
        log_level="DEBUG",
    )
