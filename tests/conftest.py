import os

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

os.environ["APP_ENV"] = "development"
os.environ["JWT_SECRET"] = "pytest-only-secret-not-for-runtime"

from app import main
from app import services
from app.db import Base, get_db
from app.rate_limit import login_rate_limit, register_rate_limit


@pytest.fixture(autouse=True)
def isolate_database(tmp_path, monkeypatch):
    test_engine = create_engine(
        f"sqlite:///{(tmp_path / 'test.db').as_posix()}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(test_engine)
    TestSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    monkeypatch.setattr(main, "engine", test_engine)
    monkeypatch.setattr(services, "load_model", lambda: None)
    monkeypatch.setattr(main.settings, "upload_dir", tmp_path / "uploads")
    monkeypatch.setattr(main.app.state, "test_session_factory", TestSessionLocal, raising=False)
    main.app.dependency_overrides[get_db] = override_get_db
    login_rate_limit.reset()
    register_rate_limit.reset()
    try:
        yield
    finally:
        main.app.dependency_overrides.pop(get_db, None)
        login_rate_limit.reset()
        register_rate_limit.reset()
        test_engine.dispose()
