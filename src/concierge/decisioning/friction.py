"""Proactive issue detection (FR-019): repeated help visits, unresolved
repeated chats, abandoned setup steps, and port-pending-too-long. The
counting/threshold logic is pure (`detect_friction`); `compute_friction_for_line`
is the thin DB-reading wrapper that gathers the raw event history.
"""

from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from concierge.decisioning.models import FrictionFlags
from concierge.persistence.event_models import DomainEvent

PORT_PENDING_THRESHOLD_DAYS = 3
# "Repeated" (spec.md Assumptions): more than one occurrence on the same
# unresolved topic within the active journey.
REPEATED_VISIT_THRESHOLD = 2


@dataclass(frozen=True)
class FrictionEvent:
    event_type: str
    occurred_at: datetime
    topic: str | None = None
    activity_code: str | None = None


def _as_utc(value: datetime) -> datetime:
    """SQLite drops tzinfo on round-trip; normalize everything to aware UTC
    before comparing, regardless of where the datetime originated."""
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


def detect_friction(events: list[FrictionEvent], as_of: datetime) -> FrictionFlags:
    as_of = _as_utc(as_of)
    help_topics: dict[str | None, int] = {}
    chat_topics: dict[str | None, int] = {}
    abandoned_codes: set[str] = set()
    port_pending_since: datetime | None = None
    port_resolved = False

    for event in events:
        occurred_at = _as_utc(event.occurred_at)
        if event.event_type == "HelpArticleViewed":
            help_topics[event.topic] = help_topics.get(event.topic, 0) + 1
        elif event.event_type == "ChatStarted":
            chat_topics[event.topic] = chat_topics.get(event.topic, 0) + 1
        elif event.event_type == "SetupAbandoned" and event.activity_code:
            abandoned_codes.add(event.activity_code)
        elif event.event_type == "NumberTransferPending":
            if port_pending_since is None or occurred_at < port_pending_since:
                port_pending_since = occurred_at
        elif event.event_type in ("NumberTransferCompleted", "NumberTransferFailed"):
            port_resolved = True

    repeated_help = any(count >= REPEATED_VISIT_THRESHOLD for count in help_topics.values())
    repeated_chat = any(count >= REPEATED_VISIT_THRESHOLD for count in chat_topics.values())

    port_pending_too_long = False
    if port_pending_since is not None and not port_resolved:
        age_days = (as_of - port_pending_since).days
        port_pending_too_long = age_days >= PORT_PENDING_THRESHOLD_DAYS

    return FrictionFlags(
        port_pending_too_long=port_pending_too_long,
        repeated_help_visit=repeated_help,
        unresolved_repeated_chat=repeated_chat,
        setup_abandoned_activity_codes=frozenset(abandoned_codes),
    )


def compute_friction_for_line(session: Session, journey_id: str, line_id: str, as_of: datetime | None = None) -> FrictionFlags:
    as_of = as_of or datetime.now(timezone.utc)
    rows = (
        session.query(DomainEvent)
        .filter(DomainEvent.journey_id == journey_id, DomainEvent.line_id == line_id)
        .all()
    )
    events = [
        FrictionEvent(
            event_type=row.event_type,
            occurred_at=row.occurred_at,
            topic=(row.attributes or {}).get("topic"),
            activity_code=(row.attributes or {}).get("activity_code"),
        )
        for row in rows
    ]
    return detect_friction(events, as_of)
