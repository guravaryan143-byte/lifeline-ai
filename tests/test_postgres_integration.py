import re
from uuid import uuid4

import pytest
from sqlalchemy import select
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import Base, create_database_engine
from app.models import Incident, Role, User


TEST_DATABASE_URL = settings.test_database_url
pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set TEST_DATABASE_URL to a dedicated PostgreSQL test database.",
)


def _database_identity(url: str) -> tuple[str | None, int | None, str | None]:
    parsed = make_url(url)
    return parsed.host, parsed.port, parsed.database


def test_postgres_test_database_persists_users_and_incidents():
    test_url = make_url(TEST_DATABASE_URL)
    test_database = test_url.database or ""
    if not re.search(r"(^|[_-])test($|[_-])", test_database, re.IGNORECASE):
        pytest.fail("TEST_DATABASE_URL must target a database with 'test' in its name.")
    if _database_identity(TEST_DATABASE_URL) == _database_identity(settings.database_url):
        pytest.fail("TEST_DATABASE_URL must be separate from DATABASE_URL.")

    engine = create_database_engine(TEST_DATABASE_URL)
    try:
        with engine.connect():
            pass
        Base.metadata.create_all(engine)

        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                with Session(
                    bind=connection,
                    join_transaction_mode="create_savepoint",
                ) as session:
                    email = f"audit-{uuid4().hex}@example.test"
                    user = User(
                        email=email,
                        password_hash="integration-test-hash",
                        role=Role.reporter,
                    )
                    session.add(user)
                    session.flush()
                    incident = Incident(
                        title="PostgreSQL integration check",
                        description="Verify database reads and writes in the test database.",
                        reporter_id=user.id,
                    )
                    session.add(incident)
                    session.commit()

                    saved_user = session.scalar(select(User).where(User.email == email))
                    saved_incident = session.scalar(
                        select(Incident).where(Incident.reporter_id == user.id)
                    )
                    assert saved_user is not None
                    assert saved_incident is not None
                    assert saved_incident.title == "PostgreSQL integration check"
            finally:
                transaction.rollback()
    except SQLAlchemyError as exc:
        pytest.fail(f"PostgreSQL test-database check failed ({type(exc).__name__}).")
    finally:
        engine.dispose()
