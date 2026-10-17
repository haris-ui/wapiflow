from functools import lru_cache
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration loaded from environment variables."""

    # Supabase credentials & JWT
    SUPABASE_URL: str = "https://example.supabase.co"
    SUPABASE_ANON_KEY: str = "example-anon-key"
    SUPABASE_SERVICE_ROLE_KEY: str = "example-service-role-key"
    SUPABASE_JWT_SECRET: str = "secret-jwt-key-with-minimum-32-characters-length"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@localhost:5432/wapiflow"

    # Application Security
    SECRET_KEY: str = "wapiflow-production-super-secret-key-32-bytes-min"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60

    # CORS
    CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://localhost:8000",
        "https://wapiflow.com",
        "https://app.wapiflow.com",
    ]

    # Cloudflare R2 Storage
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = "wapiflow-assets"
    R2_PUBLIC_URL: str = ""

    # Meta WhatsApp Cloud API
    META_APP_SECRET: str = ""
    META_VERIFY_TOKEN: str = "wapiflow_webhook_verify_token"
    META_WHATSAPP_API_VERSION: str = "v19.0"

    # Redis / ARQ
    REDIS_URL: str = "redis://localhost:6379/0"

    # Logging & Environment
    LOG_LEVEL: str = "INFO"
    DEBUG: bool = False
    ENVIRONMENT: str = "development"

    # Resend Email API
    RESEND_API_KEY: str = ""

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str):
            if v.startswith("[") and v.endswith("]"):
                import json
                try:
                    return json.loads(v)
                except Exception:
                    pass
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return []

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Return cached application settings singleton."""
    return Settings()
