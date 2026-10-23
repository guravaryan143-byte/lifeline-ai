from unittest.mock import MagicMock
from unittest.mock import patch

from sqlalchemy.dialects import sqlite
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateTable
from sqlalchemy.engine import URL

from app.db import (
    Base,
    check_database_connection,
    create_database_engine,
    run_database_diagnostic,
)
from app.models import Incident, IncidentAttachment, IncidentNote, Role, StatusHistory, User


def test_database_engine_supports_postgresql_and_sqlite():
    postgres_engine = create_database_engine(
        "postgresql+psycopg://user:password@localhost:5432/lifeline"
    )
    sqlite_engine = create_database_engine("sqlite:///:memory:")
    try:
        assert postgres_engine.dialect.name == "postgresql"
        assert postgres_engine.dialect.driver == "psycopg"
        assert isinstance(sqlite_engine.dialect, sqlite.dialect)
        for table in (User.__table__, Incident.__table__, StatusHistory.__table__,
                      IncidentNote.__table__, IncidentAttachment.__table__):
            assert "CREATE TABLE" in str(CreateTable(table).compile(dialect=postgres_engine.dialect))
        index_names = {
            index.name
            for table in (Incident.__table__, StatusHistory.__table__,
                          IncidentNote.__table__, IncidentAttachment.__table__)
            for index in table.indexes
        }
        assert {
            "ix_incidents_reporter_created_at",
            "ix_incidents_assigned_to",
            "ix_incidents_created_at",
            "ix_status_history_incident_created_at",
            "ix_status_history_actor_id",
            "ix_incident_notes_incident_created_at",
            "ix_incident_notes_author_id",
            "ix_incident_attachments_incident_created_at",
            "ix_incident_attachments_uploader_id",
        } <= index_names
    finally:
        postgres_engine.dispose()
        sqlite_engine.dispose()


def test_engine_uses_bounded_postgresql_connection_timeout():
    url = URL.create(
        "postgresql+psycopg",
        username="lifeline_app",
        password="123456",
        host="127.0.0.1",
        port=5432,
        database="lifeline_ai_dev",
    )
    with patch("app.db.create_engine") as create_engine:
        create_database_engine(url)

    assert create_engine.call_args.args[0] == url
    assert create_engine.call_args.kwargs["connect_args"] == {"connect_timeout": 5}


def test_connection_check_queries_database_and_user():
    connection = MagicMock()
    connection.execute.return_value.one.return_value = ("lifeline_ai_dev", "lifeline_app")
    test_engine = MagicMock()
    test_engine.connect.return_value.__enter__.return_value = connection

    assert check_database_connection(test_engine) == ("lifeline_ai_dev", "lifeline_app")
    assert str(connection.execute.call_args.args[0]) == (
        "SELECT current_database(), current_user"
    )


def test_connection_diagnostic_does_not_print_database_error_details(capsys):
    test_engine = MagicMock()
    test_engine.connect.side_effect = SQLAlchemyError("sensitive connection details")

    assert run_database_diagnostic(test_engine) == 1

    output = capsys.readouterr()
    assert "Database connection failed" in output.err
    assert "sensitive connection details" not in output.err
    assert "sensitive connection details" not in output.out


def test_connection_diagnostic_identifies_password_rejection_without_details(capsys):
    class DriverError(Exception):
        sqlstate = None

    error = SQLAlchemyError("sensitive wrapper detail")
    error.orig = DriverError(
        "password authentication failed for user with sensitive detail"
    )
    test_engine = MagicMock()
    test_engine.connect.side_effect = error

    assert run_database_diagnostic(test_engine) == 1

    output = capsys.readouterr()
    assert "PostgreSQL rejected the lifeline_app password" in output.err
    assert "sensitive detail" not in output.err
    assert "sensitive detail" not in output.out


def test_connection_diagnostic_identifies_unreachable_server_without_details(capsys):
    class DriverError(Exception):
        pass

    error = SQLAlchemyError("sensitive wrapper detail")
    error.orig = DriverError("connection timed out with sensitive detail")
    test_engine = MagicMock()
    test_engine.connect.side_effect = error

    assert run_database_diagnostic(test_engine) == 1

    output = capsys.readouterr()
    assert "connection timeout" in output.err
    assert "sensitive detail" not in output.err
    assert "sensitive detail" not in output.out


def test_database_records_survive_engine_restart(tmp_path):
    database_url = f"sqlite:///{(tmp_path / 'persistence.db').as_posix()}"
    first_engine = create_database_engine(database_url)
    Base.metadata.create_all(first_engine)
    first_sessions = sessionmaker(bind=first_engine)
    with first_sessions() as session:
        user = User(
            email="persisted@example.com",
            password_hash="test-hash",
            role=Role.reporter,
        )
        session.add(user)
        session.commit()
        persisted_id = user.id
        incident = Incident(
            title="Persisted incident",
            description="A database persistence test incident.",
            reporter_id=persisted_id,
        )
        session.add(incident)
        session.commit()
        persisted_incident_id = incident.id
    first_engine.dispose()

    restarted_engine = create_database_engine(database_url)
    restarted_sessions = sessionmaker(bind=restarted_engine)
    try:
        with restarted_sessions() as session:
            persisted = session.get(User, persisted_id)
            assert persisted is not None
            assert persisted.email == "persisted@example.com"
            persisted_incident = session.get(Incident, persisted_incident_id)
            assert persisted_incident is not None
            assert persisted_incident.reporter_id == persisted_id
    finally:
        restarted_engine.dispose()
