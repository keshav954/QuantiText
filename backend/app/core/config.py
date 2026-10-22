"""
Application settings loaded exclusively from environment variables.
Never hardcode secrets. Copy .env.example to .env for local development.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # ── Auth / JWT ───────────────────────────────────────
    SECRET_KEY: str = "change-this-to-a-random-64-char-string"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24 hours
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


# Singleton — import this everywhere
settings = Settings()
