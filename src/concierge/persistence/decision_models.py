import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from concierge.persistence.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class NextBestActionRecord(Base):
    """Computed per line (FR-010, Clarifications Q2); the "current" NBA for a
    line is the latest non-superseded record."""

    __tablename__ = "next_best_action_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    journey_id: Mapped[str] = mapped_column(String, index=True)
    line_id: Mapped[str] = mapped_column(String, index=True)
    action_code: Mapped[str] = mapped_column(String)
    priority: Mapped[int] = mapped_column()
    tie_break_rank: Mapped[int] = mapped_column()
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    message: Mapped[str | None] = mapped_column(String, nullable=True)
    computed_at: Mapped[datetime] = mapped_column(default=_utcnow)
    superseded_at: Mapped[datetime | None] = mapped_column(nullable=True)


class HealthScoreRecord(Base):
    """Both a per-line and a per-account record are computed (FR-016); the
    account-level score is the minimum of its lines' scores."""

    __tablename__ = "health_score_records"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    journey_id: Mapped[str] = mapped_column(String, index=True)
    line_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    score: Mapped[int] = mapped_column()
    band: Mapped[str] = mapped_column(String)
    reason_codes: Mapped[list] = mapped_column(JSON, default=list)
    computed_at: Mapped[datetime] = mapped_column(default=_utcnow)


class OutreachAttempt(Base):
    """A proactive contact delivered or suppressed (FR-014/FR-015/FR-028a).
    Cap counters (FR-014) only increment on DELIVERED attempts — a suppressed
    attempt does not consume a contact-cap slot."""

    __tablename__ = "outreach_attempts"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(String, index=True)
    line_id: Mapped[str] = mapped_column(String, index=True)
    next_best_action_id: Mapped[str] = mapped_column(String)
    channel: Mapped[str] = mapped_column(String)
    attempted_at: Mapped[datetime] = mapped_column(default=_utcnow)
    status: Mapped[str] = mapped_column(String)  # DELIVERED | SUPPRESSED
    suppression_reason: Mapped[str | None] = mapped_column(String, nullable=True)
    # DAILY_CAP | WEEKLY_CAP | QUIET_HOURS | OPTED_OUT | ESCALATION_OPEN


class EscalationCase(Base):
    __tablename__ = "escalation_cases"

    case_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    journey_id: Mapped[str] = mapped_column(String, index=True)
    line_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    reason: Mapped[str] = mapped_column(String)
    priority: Mapped[int] = mapped_column()
    related_action_code: Mapped[str | None] = mapped_column(String, nullable=True)
    """The NBA action_code (nba.py's BASE_PRIORITY keys) this escalation is
    about, if any — distinct from `reason` (why it was escalated). Used to
    suppress that specific NBA candidate while the case is open (FR-028a)."""
    journey_snapshot: Mapped[dict] = mapped_column(JSON, default=dict)
    relevant_event_ids: Mapped[list] = mapped_column(JSON, default=list)
    attempted_action_ids: Mapped[list] = mapped_column(JSON, default=list)
    conversation_summary: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String, default="OPEN")  # OPEN | RESOLVED | CLOSED
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)


class ConsentPreference(Base):
    __tablename__ = "consent_preferences"

    customer_id: Mapped[str] = mapped_column(String, primary_key=True)
    opted_out: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)
