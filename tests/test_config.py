import pytest
from pydantic import ValidationError
from sqlalchemy.engine import make_url
from pathlib import Path

from app.core.config import PROJECT_ROOT, Settings


def test_production_requires_strong_jwt_secret():
    with pytest.raises(ValidationError, match="unique JWT_SECRET"):
        Settings(
            app_env="production",
            jwt_secret="short",
            cors_origins="https://demo.example.com",
        )


def test_missing_app_env_fails_closed_in_production(monkeypatch):
    for name in (
        "APP_ENV",
        "CORS_ORIGINS",
        "DATABASE_URL",
        "DATABASE_PASSWORD",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("JWT_SECRET", "short")

    with pytest.raises(ValidationError, match="unique JWT_SECRET"):
        Settings(_env_file=None)


def test_jwt_secret_is_required_in_development(monkeypatch):
    monkeypatch.delenv("JWT_SECRET", raising=False)

    with pytest.raises(ValidationError, match="jwt_secret"):
        Settings(_env_file=None, app_env="development")


def test_local_development_must_be_explicit_when_env_file_is_disabled():
    settings = Settings(
        _env_file=None,
        app_env="development",
        jwt_secret="development-test-secret",
    )

    assert settings.app_env == "development"


def test_production_requires_https_non_local_cors_origins():
    with pytest.raises(ValidationError, match="Production CORS origins"):
        Settings(
            app_env="production",
            jwt_secret="a-unique-secret-that-is-long-enough-for-production",
            cors_origins="http://demo.example.com",
        )


def test_production_accepts_explicit_secure_configuration():
    settings = Settings(
        app_env="production",
        jwt_secret="a-unique-secret-that-is-long-enough-for-production",
        cors_origins="https://demo.example.com",
    )
    assert settings.app_env == "production"


def test_production_requires_postgresql():
    with pytest.raises(ValidationError, match="Production requires a PostgreSQL"):
        Settings(
            app_env="production",
            jwt_secret="a-unique-secret-that-is-long-enough-for-production",
            cors_origins="https://demo.example.com",
            database_url="sqlite:///./lifeline.db",
        )


def test_database_url_rejects_unsupported_driver():
    with pytest.raises(ValueError, match="DATABASE_URL must use"):
        Settings(database_url="mysql://localhost/lifeline").sqlalchemy_database_url


def test_default_database_url_targets_local_development_database_without_password():
    default_url = Settings.model_fields["database_url"].default
    parsed_url = make_url(default_url)
    assert parsed_url.drivername == "postgresql+psycopg"
    assert parsed_url.username == "lifeline_app"
    assert parsed_url.password is None
    assert parsed_url.host == "127.0.0.1"
    assert parsed_url.port == 5432
    assert parsed_url.database == "lifeline_ai_dev"


def test_database_urls_load_from_env_file(tmp_path, monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
    monkeypatch.delenv("TEST_DATABASE_URL", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_ENV=development\n"
        "DATABASE_URL=postgresql+psycopg://lifeline_app@127.0.0.1:5432/lifeline_ai_dev\n"
        "DATABASE_PASSWORD=654321\n"
        "TEST_DATABASE_URL=postgresql+psycopg://lifeline_app@localhost:5432/lifeline_ai_test\n",
        encoding="utf-8",
    )

    settings = Settings(_env_file=env_file)

    assert make_url(settings.database_url).database == "lifeline_ai_dev"
    assert settings.test_database_url is not None
    assert make_url(settings.test_database_url).database == "lifeline_ai_test"
    assert settings.sqlalchemy_database_url.password == "654321"


def test_default_env_file_is_absolute_and_in_backend_root():
    assert Settings.model_config["env_file"] == PROJECT_ROOT / ".env"
    assert Path(Settings.model_config["env_file"]).is_absolute()


def test_process_database_url_overrides_dotenv(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_ENV=development\n"
        "DATABASE_URL=postgresql+psycopg://dotenv_user@localhost:5432/dotenv_db\n",
        encoding="utf-8",
    )
    monkeypatch.setenv(
        "DATABASE_URL",
        "postgresql+psycopg://environment_user:test%40pass@localhost:5432/environment_db",
    )

    settings = Settings(_env_file=env_file)
    parsed_url = make_url(settings.database_url)

    assert parsed_url.database == "environment_db"
    assert parsed_url.username == "environment_user"
    assert parsed_url.password == "test@pass"


@pytest.mark.parametrize(
    "password",
    [
        "123456",
        "with@at",
        "with:colon",
        "with/slash",
        "with#hash",
        "with%percent",
        "mix@:/#%123",
    ],
)
def test_raw_database_password_is_safe_for_sqlalchemy_url_create(tmp_path, monkeypatch, password):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
    env_file = tmp_path / ".env"
    env_file.write_text(
        "APP_ENV=development\n"
        "DATABASE_URL=postgresql+psycopg://lifeline_app@127.0.0.1:5432/lifeline_ai_dev\n",
        encoding="utf-8",
    )

    settings = Settings(
        _env_file=env_file,
        database_password=password,
    )
    url = settings.sqlalchemy_database_url

    assert url.password == password
    assert url.drivername == "postgresql+psycopg"
    assert url.host == "127.0.0.1"
    assert url.port == 5432
    assert url.database == "lifeline_ai_dev"


def test_percent_encoded_database_url_password_is_decoded_once(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("DATABASE_PASSWORD", raising=False)
    raw_password = "mix@:/#%123"
    settings = Settings(
        _env_file=None,
        app_env="development",
        database_url=(
            "postgresql+psycopg://lifeline_app:mix%40%3A%2F%23%25123"
            "@127.0.0.1:5432/lifeline_ai_dev"
        )
    )

    assert settings.sqlalchemy_database_url.password == raw_password


@pytest.mark.parametrize(
    "database_url",
    [
        "postgresql+psycopg://lifeline_app@127.0.0.1:invalid/lifeline_ai_dev",
        "postgresql+psycopg:///lifeline_ai_dev",
        "postgresql+psycopg://lifeline_app@127.0.0.1/",
        "mysql://lifeline_app@127.0.0.1:3306/lifeline_ai_dev",
    ],
)
def test_database_url_rejects_malformed_or_unsupported_configuration(database_url):
    settings = Settings(database_url=database_url)

    with pytest.raises(ValueError, match="DATABASE_URL"):
        settings.sqlalchemy_database_url
