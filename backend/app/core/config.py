"""Application configuration loaded from environment variables."""
from functools import lru_cache
from typing import List, Optional

from pydantic import AnyHttpUrl, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Centralized settings with sensible defaults for local development."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Application
    APP_NAME: str = "InfraGuard"
    APP_VERSION: str = "1.0.0"
    APP_ENV: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Server
    HOST: str = "0.0.0.0"
    PORT: int = 8000

    # Database (SQLite)
    DATABASE_URL: str = "sqlite:///./infraguard.db"

    # JWT
    JWT_SECRET_KEY: str = "change_this_to_a_long_random_string_in_production_5f8a2b9c1e7d"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS (allow all for prototype)
    BACKEND_CORS_ORIGINS: List[str] = ["*"]

    # File uploads
    UPLOAD_DIR: str = "./uploads"
    MAX_UPLOAD_SIZE_MB: int = 10
    ALLOWED_IMAGE_TYPES: List[str] = ["image/jpeg", "image/png", "image/webp"]

    # AI
    AI_MODEL_PATH: str = "./ai/models/severity_classifier.joblib"
    AI_CONFIDENCE_THRESHOLD: float = 0.55
    AI_USE_GPU: bool = False

    # LLM (optional — for Llama 3 / GPT-4o Vision image analysis)
    # If LLM_API_KEY is unset, the system falls back to scikit-learn classifier.
    LLM_API_KEY: str = ""  # set this to enable LLM image analysis
    LLM_API_BASE_URL: str = "https://api.groq.com/openai/v1"
    LLM_VISION_MODEL: str = "meta-llama/llama-4-scout-17b-16e-instruct"

    # Default admin
    DEFAULT_ADMIN_EMAIL: str = "admin@infraguard.gov"
    DEFAULT_ADMIN_PASSWORD: str = "Admin@12345"
    DEFAULT_ADMIN_NAME: str = "System Administrator"

    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def _split_cors(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    """Cached settings accessor."""
    return Settings()


settings = get_settings()
