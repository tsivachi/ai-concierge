import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from concierge.persistence.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DomainEvent(Base):
    """Immutable append-only event log (FR-007). Idempotency is checked via
    ProcessedEvent, not by this table's presence alone, so a dead-lettered
    event can still be recorded here for audit purposes."""

    __tablename__ = "domain_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    event_type: Mapped[str] = mapped_column(String, index=True)
    customer_id: Mapped[str] = mapped_column(String, index=True)
    account_id: Mapped[str] = mapped_column(String, index=True)
    line_id: Mapped[str | None] = mapped_column(String, nullable=True)
    journey_id: Mapped[str | None] = mapped_column(String, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column()
    source: Mapped[str] = mapped_column(String)
    correlation_id: Mapped[str] = mapped_column(String, index=True)
    attributes: Mapped[dict] = mapped_column(JSON, default=dict)
    received_at: Mapped[datetime] = mapped_column(default=_utcnow)


class ProcessedEvent(Base):
    """Dedupe index (FR-008): a row's existence here is the idempotency check.
    A second delivery with the same event_id short-circuits before any state
    mutation is applied."""

    __tablename__ = "processed_events"

    event_id: Mapped[str] = mapped_column(String, primary_key=True)
    processed_at: Mapped[datetime] = mapped_column(default=_utcnow)


class DeadLetterEvent(Base):
    """Events referencing an unknown account/line (FR-009a): logged without
    any state mutation. A later resubmission with the same event_id, once the
    entity exists, is processed normally (it never reached ProcessedEvent)."""

    __tablename__ = "dead_letter_events"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    event_id: Mapped[str] = mapped_column(String, index=True)
    event_type: Mapped[str] = mapped_column(String)
    account_id: Mapped[str] = mapped_column(String, index=True)
    line_id: Mapped[str | None] = mapped_column(String, nullable=True)
    reason: Mapped[str] = mapped_column(String)  # UNKNOWN_ACCOUNT | UNKNOWN_LINE
    raw_payload: Mapped[dict] = mapped_column(JSON)
    logged_at: Mapped[datetime] = mapped_column(default=_utcnow)


class StateTransitionLog(Base):
    """Auditable entry for every activity/health/NBA-affecting state change
    (FR-009; Constitution Principle VI). Written for ACTIVITY_INSTANCE,
    ACCOUNT_JOURNEY, HEALTH_SCORE, NEXT_BEST_ACTION, and ESCALATION_CASE
    changes alike — not just activity transitions (closes analyze finding H3)."""

    __tablename__ = "state_transition_log"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    journey_id: Mapped[str] = mapped_column(String, index=True)
    line_id: Mapped[str | None] = mapped_column(String, nullable=True)
    entity_type: Mapped[str] = mapped_column(String)
    entity_id: Mapped[str] = mapped_column(String)
    before_state: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    after_state: Mapped[dict] = mapped_column(JSON)
    triggering_event_id: Mapped[str | None] = mapped_column(String, nullable=True)
    occurred_at: Mapped[datetime] = mapped_column(default=_utcnow)
    correlation_id: Mapped[str | None] = mapped_column(String, nullable=True)
