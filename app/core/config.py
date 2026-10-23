from pathlib import Path
from typing import Literal
from urllib.parse import urlsplit

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from sqlalchemy.exc import ArgumentError
from sqlalchemy.engine import URL, make_url

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    app_name: str = "LifeLine AI"
    database_url: str = "postgresql+psycopg://lifeline_app@127.0.0.1:5432/lifeline_ai_dev"
    database_password: SecretStr | None = None
    test_database_url: str | None = None
    jwt_secret: str = "development-only-change-this-secret"
    jwt_expire_minutes: int = 60
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    app_env: Literal["development", "production"] = "production"
    upload_dir: Path = Path("./uploads")
    max_upload_size_mb: int = 5
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", extra="ignore")

    @field_validator("cors_origins")
    @classmethod
    def validate_cors_origins(cls, value: str) -> str:
        origins = [origin.strip() for origin in value.split(",") if origin.strip()]
        if not origins or "*" in origins:
            raise ValueError("CORS_ORIGINS must contain explicit origins and cannot contain '*'.")
        for origin in origins:
            parsed = urlsplit(origin)
            if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.path not in {"", "/"}:
                raise ValueError(f"Invalid CORS origin: {origin}")
        return ",".join(origins)

    @property
    def sqlalchemy_database_url(self) -> URL:
        try:
            parsed = make_url(self.database_url)
        except (ArgumentError, TypeError, ValueError):
            raise ValueError(
                "DATABASE_URL is malformed. Check its driver, host, port, and database."
            ) from None

        if parsed.drivername not in {"sqlite", "postgresql+psycopg"}:
            raise ValueError(
                "DATABASE_URL must use sqlite or postgresql+psycopg."
            )
        if parsed.drivername == "postgresql+psycopg" and (
            not parsed.host or not parsed.database or not parsed.username
        ):
            raise ValueError(
                "DATABASE_URL must include a PostgreSQL host, database, and username."
            )

        password = (
            self.database_password.get_secret_value()
            if self.database_password is not None
            else parsed.password
        )
        return URL.create(
            drivername=parsed.drivername,
            username=parsed.username,
            password=password,
            host=parsed.host,
            port=parsed.port,
            database=parsed.database,
            query=parsed.query,
        )

    @field_validator("test_database_url")
    @classmethod
    def validate_test_database_url(cls, value: str | None) -> str | None:
        if value and value.split(":", maxsplit=1)[0] != "postgresql+psycopg":
            raise ValueError("TEST_DATABASE_URL must use postgresql+psycopg.")
        return value or None

    @model_validator(mode="after")
    def validate_security_settings(self):
        if self.app_env == "production" and (
            len(self.jwt_secret) < 32
            or self.jwt_secret == "development-only-change-this-secret"
            or self.jwt_secret == "replace-with-a-long-random-secret-before-use"
        ):
            raise ValueError("Production requires a unique JWT_SECRET of at least 32 characters.")
        if self.app_env == "production":
            if not self.database_url.startswith("postgresql+psycopg://"):
                raise ValueError("Production requires a PostgreSQL DATABASE_URL.")
            for origin in self.cors_origins.split(","):
                parsed = urlsplit(origin)
                if parsed.scheme != "https" or parsed.hostname in {"localhost", "127.0.0.1", "::1"}:
                    raise ValueError("Production CORS origins must use HTTPS and cannot be localhost.")
        if self.jwt_expire_minutes < 1:
            raise ValueError("JWT_EXPIRE_MINUTES must be positive.")
        if self.max_upload_size_mb < 1:
            raise ValueError("MAX_UPLOAD_SIZE_MB must be positive.")
        return self

settings = Settings()
