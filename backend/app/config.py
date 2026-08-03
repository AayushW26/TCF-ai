"""
Application configuration loaded from environment variables.
Uses pydantic-settings for validation and type coercion.
"""

from functools import lru_cache
from typing import List

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Central configuration — all values sourced from .env or env vars."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── Supabase ──────────────────────────────────────────
    supabase_url: str
    supabase_service_key: str

    # ── Redis (Upstash) ──────────────────────────────────
    redis_url: str

    # ── Google Gemini ─────────────────────────────────────
    gemini_api_key: str

    # ── Meta WhatsApp Cloud API ───────────────────────────
    meta_access_token: str
    meta_phone_number_id: str
    whatsapp_verify_token: str
    meta_app_secret: str

    # ── Cloudmailin (Email Ingestion) ─────────────────────
    cloudmailin_secret: str
    cloudmailin_email_domain: str = "munim.cloudmailin.net"

    # ── DeepVue.tech (GSTIN Validation) ──────────────────
    deepvue_api_key: str
    deepvue_client_id: str

    # ── JWT Auth ──────────────────────────────────────────
    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    jwt_expiry_minutes: int = 1440  # 24 hours

    # ── Application ──────────────────────────────────────
    app_env: str = "development"
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> List[str]:
        """Parse comma-separated CORS origins into a list."""
        return [origin.strip() for origin in self.cors_origins.split(",")]

    @property
    def is_production(self) -> bool:
        return self.app_env == "production"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton — loaded once per process."""
    return Settings()
