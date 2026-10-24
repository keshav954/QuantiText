"""
Application settings loaded exclusively from environment variables.
Never hardcode secrets. Copy .env.example to .env for local development.
"""

from __future__ import annotations

import logging
import sys

from pydantic_settings import BaseSettings, SettingsConfigDict

log = logging.getLogger(__name__)

_DEFAULT_SECRET = "change-this-to-a-random-64-char-string"


class Settings(BaseSettings):
    """
    All configuration is read from environment variables (or .env file).
    Fields use UPPER_SNAKE_CASE matching the env var names exactly.
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # ── App ──────────────────────────────────────────────
    APP_NAME: str = "QuantiText"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # ── CORS (comma-separated origins) ───────────────────
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    # ── PostgreSQL ───────────────────────────────────────
    DATABASE_URL: str = "postgresql+asyncpg://quantitext:changeme_dev_only@postgres:5432/quantitext"
    DATABASE_URL_SYNC: str = (
        "postgresql+psycopg2://quantitext:changeme_dev_only@postgres:5432/quantitext"
    )
    DB_READONLY_URL: str = (
        "postgresql+asyncpg://quantitext:changeme_dev_only@postgres:5432/quantitext"
    )

    # ── Redis ────────────────────────────────────────────
    REDIS_URL: str = "redis://redis:6379/0"
    REDIS_PASSWORD: str = ""

    # ── Auth / JWT ───────────────────────────────────────
    SECRET_KEY: str = _DEFAULT_SECRET
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60  # 1 hour
    ALGORITHM: str = "HS256"

    # ── LLM Provider ─────────────────────────────────────
    LLM_PROVIDER: str = "auto"  # ollama | gemini | auto
    GEMINI_API_KEY: str = ""
    LLM_MODEL: str = "gemini-3.5-flash"

    # ── Ollama (local LLM) ───────────────────────────────
    OLLAMA_BASE_URL: str = "http://ollama:11434"
    OLLAMA_SQL_MODEL: str = "qwen2.5-coder:7b"
    OLLAMA_TEXT_MODEL: str = "llama3:8b"

    # ── Embeddings ───────────────────────────────────────
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    EMBEDDING_DIMENSION: int = 384

    # ── MLflow ───────────────────────────────────────────
    MLFLOW_TRACKING_URI: str = "http://localhost:5000"

    # ── SQL Safety (seconds) ─────────────────────────────
    SQL_STATEMENT_TIMEOUT: int = 10

    @property
    def cors_origin_list(self) -> list[str]:
        """Parse comma-separated CORS_ORIGINS into a list."""
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]


# Singleton — import this everywhere
settings = Settings()


_INSECURE_SECRET_SUBSTRINGS = (
    "generate",
    "change",
    "set_strong",
    "placeholder",
    "secret",
    "default",
    "quantitext",
)


def validate_production_settings() -> None:
    """
    Called at startup. Refuses to boot in production with insecure defaults or placeholders.
    Rejects keys shorter than 32 characters or containing placeholder words.
    """
    if not settings.DEBUG:
        key = settings.SECRET_KEY.lower().strip()
        if (
            len(settings.SECRET_KEY) < 32
            or settings.SECRET_KEY == _DEFAULT_SECRET
            or any(sub in key for sub in _INSECURE_SECRET_SUBSTRINGS)
        ):
            log.critical(
                "FATAL: Insecure SECRET_KEY detected in production environment. "
                "SECRET_KEY must be at least 32 characters long and cannot be a placeholder "
                "(rejected if shorter than 32 characters or contains 'generate', 'change', 'set_strong'). "
                "Generate a cryptographically secure key with: openssl rand -hex 32"
            )
            sys.exit(1)
