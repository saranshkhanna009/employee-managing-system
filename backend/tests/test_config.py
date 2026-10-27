from app.config import Settings, normalize_database_url


def test_normalize_database_url_accepts_render_postgres_schemes() -> None:
    assert normalize_database_url("postgres://user:pass@host/db") == (
        "postgresql+asyncpg://user:pass@host/db"
    )
    assert normalize_database_url("postgresql://user:pass@host/db") == (
        "postgresql+asyncpg://user:pass@host/db"
    )
    assert normalize_database_url("postgresql+asyncpg://user:pass@host/db") == (
        "postgresql+asyncpg://user:pass@host/db"
    )


def test_explicit_base64_keys_validate() -> None:
    key = "YWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWFhYWE="
    settings = Settings(ENCRYPTION_MASTER_KEY=key, SECRET_KEY=key)

    assert settings.ENCRYPTION_MASTER_KEY == key
    assert settings.SECRET_KEY == key
