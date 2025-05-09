# backend/app/config.py
from pydantic_settings import BaseSettings
from typing import List, Optional
from functools import lru_cache
import os


class Settings(BaseSettings):
    """Application settings with environment variable loading"""

    # General settings
    APP_NAME: str = "Finexia API"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    API_V1_PREFIX: str = "/api/v1"

    # CORS settings
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8000", "https://finexia.app"]

    # Database connection
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql+psycopg2://postgres:password@localhost:5432/finexia-mt")

    # Authentication
    SECRET_KEY: str = os.getenv("SECRET_KEY", "finexia_mt_2025")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Multi-tenant settings
    DEFAULT_TENANT_SLUG: Optional[str] = None
    TENANT_HEADER_NAME: str = "X-Tenant"

    # Rate limiting
    RATE_LIMIT_REQUESTS: int = 100
    RATE_LIMIT_WINDOW: int = 60  # seconds

    # Model storage
    MODEL_STORAGE_PATH: str = os.getenv("MODEL_STORAGE_PATH", "./models")

    # Cache settings
    CACHE_TTL: int = 60 * 5  # 5 minutes

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True


@lru_cache
def get_settings() -> Settings:
    """Create cached settings instance"""
    return Settings()


# Export settings for use in other modules
settings = get_settings()
