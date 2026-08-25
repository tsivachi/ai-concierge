import os
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    """Shared declarative base for every SQLAlchemy 2.0 model in this package."""


def _database_url() -> str:
    # SQLite default for zero-friction local demo; swapping DATABASE_URL to a
    # PostgreSQL DSN is the only change needed to target Postgres (research.md §2).
    return os.environ.get("DATABASE_URL", "sqlite:///./concierge.db")


_engine = None
_SessionLocal: sessionmaker[Session] | None = None


def get_engine():
    global _engine
    if _engine is None:
        url = _database_url()
        connect_args = {"check_same_thread": False} if url.startswith("sqlite") else {}
        _engine = create_engine(url, connect_args=connect_args)
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    global _SessionLocal
    if _SessionLocal is None:
        _SessionLocal = sessionmaker(bind=get_engine(), expire_on_commit=False)
    return _SessionLocal


def init_db() -> None:
    """Create every table registered on Base.metadata (idempotent)."""
    Base.metadata.create_all(bind=get_engine())


def reset_db_for_tests() -> None:
    """Drop and recreate all tables — used by tests and the scenario loader's
    truncate-and-reload semantics (FR-032)."""
    Base.metadata.drop_all(bind=get_engine())
    Base.metadata.create_all(bind=get_engine())


@contextmanager
def session_scope() -> Iterator[Session]:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
