import pytest


@pytest.fixture()
def db_session(tmp_path, monkeypatch):
    """A fresh SQLite-backed session per test, isolated via a temp file so
    tests never share or leak state (mirrors the scenario-reset guarantee,
    SC-011, at the test-infrastructure level)."""
    db_path = tmp_path / "test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    import concierge.persistence.db as db_module

    db_module._engine = None
    db_module._SessionLocal = None

    from concierge.persistence import (  # noqa: F401
        billing_models,
        conversation_models,
        decision_models,
        event_models,
        models,
    )

    db_module.init_db()
    session = db_module.get_session_factory()()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture()
def api_client(tmp_path, monkeypatch):
    """A TestClient wired to its own isolated SQLite file, with the FastAPI
    lifespan (startup -> init_db) actually triggered."""
    db_path = tmp_path / "api_test.db"
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")

    import concierge.persistence.db as db_module

    db_module._engine = None
    db_module._SessionLocal = None

    from fastapi.testclient import TestClient

    from apps.api.main import app

    with TestClient(app) as client:
        yield client
