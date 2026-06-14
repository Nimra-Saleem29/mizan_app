"""
Wakeel وکیل — Application Configuration
=========================================
All settings are loaded from environment variables (or a .env file).
Pydantic-settings validates types and provides helpful error messages
if required variables are missing.

Usage:
    from config import settings
    print(settings.SUPABASE_URL)
"""

from functools import lru_cache
from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",       # silently ignore unknown env vars
    )

    # ── Core ──────────────────────────────────────────────────────────────────
    ENVIRONMENT: str = Field(default="development", description="development | staging | production")
    DEBUG: bool = Field(default=True)
    SECRET_KEY: str = Field(default="change-me-in-production", min_length=16)
    APP_NAME: str = "Wakeel"

    # ── Supabase ──────────────────────────────────────────────────────────────
    SUPABASE_URL: str = Field(description="Your Supabase project URL")
    SUPABASE_KEY: str = Field(description="Supabase anon key (public, used server-side for RLS)")
    SUPABASE_SERVICE_ROLE_KEY: str = Field(
        default="",
        description="Service role key — bypasses RLS. Use only for admin operations."
    )

    # ── AI — Google Gemini ────────────────────────────────────────────────────
    GEMINI_API_KEY: str = Field(description="Google AI Studio API key")
    GEMINI_MODEL: str = Field(default="gemini-1.5-flash")
    GEMINI_MAX_TOKENS: int = Field(default=2048, ge=256, le=8192)
    GEMINI_TEMPERATURE: float = Field(default=0.2, ge=0.0, le=1.0)

    # ── AI — Hugging Face ─────────────────────────────────────────────────────
    HUGGINGFACE_TOKEN: str = Field(default="")
    HF_EMBEDDING_MODEL: str = Field(default="sentence-transformers/all-MiniLM-L6-v2")

    # ── AI — OpenAI Whisper ───────────────────────────────────────────────────
    OPENAI_API_KEY: str = Field(default="")
    WHISPER_MODEL_SIZE: str = Field(default="medium")   # tiny|base|small|medium|large

    # ── Vector DB ─────────────────────────────────────────────────────────────
    FAISS_INDEX_PATH: str = Field(default="./rag/indices/wakeel_legal.faiss")
    CHROMA_PERSIST_DIR: str = Field(default="./rag/chroma_db")
    VECTOR_SEARCH_TOP_K: int = Field(default=5, ge=1, le=20)

    # ── OCR ───────────────────────────────────────────────────────────────────
    TESSERACT_CMD: str = Field(default="/usr/bin/tesseract")
    OCR_LANGUAGES: str = Field(default="urd+eng")

    # ── File Storage ──────────────────────────────────────────────────────────
    UPLOAD_DIR: str = Field(default="./uploads")
    MAX_UPLOAD_SIZE_MB: int = Field(default=10, ge=1, le=50)

    # ── CORS ──────────────────────────────────────────────────────────────────
    # In development, allow all. In production, set explicit origins.
    EXTRA_CORS_ORIGINS: List[str] = Field(default_factory=list)

    # ── Validators ────────────────────────────────────────────────────────────
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = {"development", "staging", "production"}
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT must be one of {allowed}, got '{v}'")
        return v

    @field_validator("SUPABASE_URL")
    @classmethod
    def validate_supabase_url(cls, v: str) -> str:
        if v and not v.startswith("https://"):
            raise ValueError("SUPABASE_URL must start with 'https://'")
        return v

    # ── Computed properties ───────────────────────────────────────────────────
    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT == "production"

    @property
    def is_development(self) -> bool:
        return self.ENVIRONMENT == "development"

    @property
    def cors_origins(self) -> List[str]:
        """
        Development: allow all origins (Expo Go, Metro, emulators).
        Production: only explicitly listed origins.
        """
        if self.is_development:
            return ["*"]

        default_prod_origins = [
            "https://wakeel.app",
            "https://www.wakeel.app",
            "https://app.wakeel.app",
        ]
        return default_prod_origins + self.EXTRA_CORS_ORIGINS

    @property
    def max_upload_bytes(self) -> int:
        return self.MAX_UPLOAD_SIZE_MB * 1024 * 1024


# ── Singleton ─────────────────────────────────────────────────────────────────
# @lru_cache ensures Settings() is only instantiated once — safe for FastAPI's
# dependency injection and import-time usage.
@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()  # type: ignore[call-arg]


settings: Settings = get_settings()
