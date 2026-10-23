import sys

from sqlalchemy import create_engine, text
from sqlalchemy.exc import ArgumentError
from sqlalchemy.engine import URL, make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from app.core.config import settings


def create_database_engine(database_url: str | URL) -> Engine:
    try:
        url = make_url(database_url) if isinstance(database_url, str) else database_url
    except (ArgumentError, TypeError, ValueError):
        raise ValueError(
            "Database URL is malformed. Check its driver, host, port, and database."
        ) from None

    if url.drivername not in {"sqlite", "postgresql+psycopg"}:
        raise ValueError("Database URL must use sqlite or postgresql+psycopg.")

    connect_args = (
        {"check_same_thread": False}
        if url.drivername == "sqlite"
        else {"connect_timeout": 5}
    )
    return create_engine(url, connect_args=connect_args, pool_pre_ping=True)


engine = create_database_engine(settings.sqlalchemy_database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def check_database_connection(database_engine: Engine = engine) -> tuple[str, str]:
    with database_engine.connect() as connection:
        database_name, username = connection.execute(
            text("SELECT current_database(), current_user")
        ).one()
    return database_name, username


def run_database_diagnostic(database_engine: Engine = engine) -> int:
    try:
        database_name, username = check_database_connection(database_engine)
    except SQLAlchemyError as exc:
        original_error = getattr(exc, "orig", None)
        sqlstate = getattr(original_error, "sqlstate", None)
        error_summary = str(original_error).lower() if original_error is not None else ""
        if sqlstate == "28P01" or "password authentication failed" in error_summary:
            print(
                "PostgreSQL rejected the lifeline_app password. "
                "Reset it with the PostgreSQL administrator if needed, then set "
                "DATABASE_PASSWORD in the backend .env file to the same raw "
                "password. No credentials were displayed.",
                file=sys.stderr,
            )
            return 1
        if sqlstate == "3D000":
            print(
                "The configured PostgreSQL database does not exist. Check "
                "DATABASE_URL's database name. No credentials were displayed.",
                file=sys.stderr,
            )
            return 1
        if any(
            phrase in error_summary
            for phrase in ("connection refused", "connection timed out", "timeout expired")
        ) or type(original_error).__name__ == "ConnectionTimeout":
            print(
                "PostgreSQL did not respond before the connection timeout or "
                "refused the connection. Check that the service is running and "
                "DATABASE_URL has the correct host and port. No credentials were displayed.",
                file=sys.stderr,
            )
            return 1
        print(
            "Database connection failed. Check PostgreSQL availability, the "
            "configured application password, and the database URL. Ensure "
            "special characters in URL passwords are percent-encoded, or set "
            "DATABASE_PASSWORD to the raw password. No credentials were displayed.",
            file=sys.stderr,
        )
        return 1

    print(f"Connected: database={database_name}, user={username}")
    return 0


class Base(DeclarativeBase):
    pass


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(run_database_diagnostic())
