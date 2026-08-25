"""Shared FastAPI dependencies: DB session + demo auth (research.md §5).

Demo auth is intentionally minimal and explicitly non-production (production
IAM is a stated non-goal, spec.md Assumptions): POST /api/auth/login issues
an opaque bearer token held in-memory for the process lifetime, mapping to a
customer_id. `get_current_customer` resolves the Authorization header to a
customer_id or returns None for an unauthenticated request — callers decide
what that means for their route (401 required vs. optional).
"""

import secrets

from fastapi import Header
from sqlalchemy.orm import Session

from concierge.persistence.db import get_session_factory

# In-memory session-token store: {token: customer_id}. Cleared on restart —
# there is no session-timeout/expiry behavior in this MVP (spec.md Assumptions).
_SESSIONS: dict[str, str] = {}


def issue_session_token(customer_id: str) -> str:
    token = secrets.token_urlsafe(24)
    _SESSIONS[token] = customer_id
    return token


def resolve_token(token: str) -> str | None:
    return _SESSIONS.get(token)


def get_db() -> Session:
    session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_current_customer(authorization: str | None = Header(default=None)) -> str | None:
    """Returns the authenticated customer_id, or None if the request carries
    no valid bearer token (i.e. is unauthenticated)."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    return resolve_token(token)
