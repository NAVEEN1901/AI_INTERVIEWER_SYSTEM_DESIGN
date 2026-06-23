"""AI Talent Acquisition Platform - Core Configuration."""

import os
from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Application
    APP_NAME: str = "AI Talent Acquisition Platform"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/talent_platform"
    DB_ECHO: bool = False

    # JWT
    SECRET_KEY: str = "change-this-secret-key-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # File Upload
    UPLOAD_DIR: str = "uploads/resumes"
    MAX_FILE_SIZE_MB: int = 10

    # LLM Configuration
    OPENAI_API_KEY: str = ""
    AZURE_OPENAI_ENDPOINT: str = ""
    LLM_MODEL: str = "gpt-4o-mini"

    # Base directory
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent

    model_config = {"env_file": ".env", "case_sensitive": True}


settings = Settings()
