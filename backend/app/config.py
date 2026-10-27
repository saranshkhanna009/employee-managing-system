"""Application configuration using Pydantic Settings."""

import base64
import secrets
from functools import lru_cache
from typing import List, Optional


from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


def normalize_database_url(value: str) -> str:
    """Normalize provider PostgreSQL URLs for SQLAlchemy's asyncpg engine."""
    replacements = (
        ("postgres://", "postgresql+asyncpg://"),
        ("postgresql://", "postgresql+asyncpg://"),
        ("postgresql+psycopg2://", "postgresql+asyncpg://"),
    )
    for source, target in replacements:
        if value.startswith(source):
            return target + value[len(source):]
    return value


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # Environment
    ENVIRONMENT: str = Field(default="development", description="Environment name")
    DEBUG: bool = Field(default=False, description="Debug mode")

    # Database
    DATABASE_URL: str = Field(
        default="postgresql+asyncpg://employee_user:secure_password@localhost:5432/employee_tracker",
        description="PostgreSQL async connection URL",
    )

    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def normalize_database_url_setting(cls, value: str) -> str:
        return normalize_database_url(value)

    # Redis
    REDIS_URL: str = Field(
        default="redis://:redis_password@localhost:6379/0",
        description="Redis connection URL",
    )

    # Encryption - MUST be set in production
    ENCRYPTION_MASTER_KEY: str = Field(
        default="",
        description="Base64-encoded 32-byte master encryption key",
    )
    ENCRYPTION_KEY_VERSION: int = Field(default=1, description="Key version for rotation")

    # Session Security - MUST be set in production
    SECRET_KEY: str = Field(
        default="",
        description="Base64-encoded 32-byte secret key for session signing",
    )
    SESSION_COOKIE_NAME: str = Field(default="__Host-session", description="Session cookie name")
    SESSION_COOKIE_DOMAIN: Optional[str] = Field(default=None, description="Cookie domain")
    SESSION_COOKIE_SECURE: bool = Field(default=True, description="Secure cookie flag")
    SESSION_COOKIE_HTTPONLY: bool = Field(default=True, description="HttpOnly cookie flag")
    SESSION_COOKIE_SAMESITE: str = Field(default="strict", description="SameSite policy")
    SESSION_TTL_SECONDS: int = Field(default=3600, description="Session TTL in seconds (1 hour)")
    SESSION_MAX_CONCURRENT: int = Field(default=3, description="Max concurrent sessions per user")

    # CORS
    CORS_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:5173"],
        description="Allowed CORS origins",
    )

    # Rate Limiting
    RATE_LIMIT_ENABLED: bool = Field(default=True, description="Enable rate limiting")
    RATE_LIMIT_LOGIN: str = Field(default="5/minute", description="Login rate limit")
    RATE_LIMIT_REGISTER: str = Field(default="3/hour", description="Registration rate limit")
    RATE_LIMIT_API: str = Field(default="100/minute", description="General API rate limit")
    RATE_LIMIT_PASSWORD_RESET: str = Field(default="2/hour", description="Password reset rate limit")

    # Password Security
    PASSWORD_MIN_LENGTH: int = Field(default=12, description="Minimum password length")
    PASSWORD_REQUIRE_UPPER: bool = Field(default=True, description="Require uppercase")
    PASSWORD_REQUIRE_LOWER: bool = Field(default=True, description="Require lowercase")
    PASSWORD_REQUIRE_DIGIT: bool = Field(default=True, description="Require digit")
    PASSWORD_REQUIRE_SPECIAL: bool = Field(default=True, description="Require special char")
    ARGON2_TIME_COST: int = Field(default=3, description="Argon2 time cost")
    ARGON2_MEMORY_COST: int = Field(default=65536, description="Argon2 memory cost (KB)")
    ARGON2_PARALLELISM: int = Field(default=4, description="Argon2 parallelism")

    # Email (for password reset)
    SMTP_HOST: Optional[str] = Field(default=None, description="SMTP host")
    SMTP_PORT: int = Field(default=587, description="SMTP port")
    SMTP_USER: Optional[str] = Field(default=None, description="SMTP username")
    SMTP_PASS: Optional[str] = Field(default=None, description="SMTP password")
    SMTP_TLS: bool = Field(default=True, description="Use TLS for SMTP")
    FROM_EMAIL: str = Field(default="noreply@employee-tracker.local", description="From email address")

    # Security Headers
    CSP_POLICY: str = Field(
        default=(
            "default-src 'self'; "
            "script-src 'self'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data:; "
            "font-src 'self'; "
            "connect-src 'self'; "
            "frame-ancestors 'none'; "
            "base-uri 'self'; "
            "form-action 'self'"
        ),
        description="Content Security Policy",
    )
    HSTS_MAX_AGE: int = Field(default=31536000, description="HSTS max age (1 year)")

    # Audit
    AUDIT_LOG_ENABLED: bool = Field(default=True, description="Enable audit logging")
    AUDIT_LOG_RETENTION_DAYS: int = Field(default=2555, description="Audit log retention (7 years)")

    # Admin ID Format
    ADMIN_ID_PREFIX: str = Field(default="EMP", description="Admin ID prefix")
    ADMIN_ID_FORMAT: str = Field(default="{prefix}-{company_slug}-{sequence:04d}", description="Admin ID format")

    @field_validator("ENCRYPTION_MASTER_KEY")
    @classmethod
    def validate_encryption_key(cls, v: str) -> str:
        if not v:
            # Generate a warning key for development only
            return base64.b64encode(secrets.token_bytes(32)).decode()
        # Validate it's valid base64 and 32 bytes
        try:
            decoded = base64.b64decode(v)
            if len(decoded) != 32:
                raise ValueError("ENCRYPTION_MASTER_KEY must be 32 bytes (base64 encoded)")
        except Exception as e:
            raise ValueError(f"Invalid ENCRYPTION_MASTER_KEY: {e}")
        return v

    @field_validator("SECRET_KEY")
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        if not v:
            return base64.b64encode(secrets.token_bytes(32)).decode()
        try:
            decoded = base64.b64decode(v)
            if len(decoded) != 32:
                raise ValueError("SECRET_KEY must be 32 bytes (base64 encoded)")
        except Exception as e:
            raise ValueError(f"Invalid SECRET_KEY: {e}")
        return v

    @field_validator("SESSION_COOKIE_SAMESITE")
    @classmethod
    def validate_samesite(cls, v: str) -> str:
        v = v.lower()
        if v not in ("strict", "lax", "none"):
            raise ValueError("SESSION_COOKIE_SAMESITE must be 'strict', 'lax', or 'none'")
        return v


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
