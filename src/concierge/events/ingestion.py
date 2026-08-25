"""Idempotent event ingestion (FR-008), dead-letter handling for unknown
account/line references (FR-009a), and delegation to JourneyOrchestrator for
activity-state effects (T034)."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy.orm import Session

from concierge.decisioning.recompute import recompute_line
from concierge.domain.enums import EventType
from concierge.journey.enrollment import enroll_line_on_order_completed
from concierge.journey.orchestrator import apply_event_to_journey
from concierge.persistence.repositories import EventRepository, JourneyRepository

REQUIRED_FIELDS = ("event_id", "event_type", "customer_id", "account_id", "occurred_at", "source", "correlation_id")

# OrderCompleted is the one event allowed to arrive with no existing journey —
# its job is to *create* the journey (FR-001, journey/enrollment.py).
EVENTS_REQUIRING_EXISTING_JOURNEY = frozenset(e.value for e in EventType if e != EventType.ORDER_COMPLETED)


class InvalidEventError(Exception):
    pass


@dataclass(frozen=True)
class IngestResult:
    event_id: str
    outcome: str  # applied | duplicate | dead_lettered
    dead_letter_reason: str | None = None


def _parse_occurred_at(value) -> datetime:
    if isinstance(value, datetime):
        return value
    return datetime.fromisoformat(value)


def ingest_event(session: Session, payload: dict) -> IngestResult:
    missing = [f for f in REQUIRED_FIELDS if not payload.get(f)]
    if missing:
        raise InvalidEventError(f"missing required field(s): {', '.join(missing)}")

    event_id = payload["event_id"]
    event_type = payload["event_type"]
    account_id = payload["account_id"]
    line_id = payload.get("line_id")

    event_repo = EventRepository(session)
    journey_repo = JourneyRepository(session)

    # FR-008: idempotency — a duplicate event_id is a safe no-op.
    if event_repo.is_processed(event_id):
        return IngestResult(event_id=event_id, outcome="duplicate")

    occurred_at = _parse_occurred_at(payload["occurred_at"])

    if event_type == EventType.ORDER_COMPLETED.value:
        if line_id is None:
            raise InvalidEventError("OrderCompleted requires line_id")

        if journey_repo.get_line(line_id) is not None:
            # Already enrolled (e.g. a demo scenario pre-seeded this line
            # directly) — OrderCompleted is then just a no-op signal, not a
            # fresh enrollment, so no attributes.plan_type is required.
            journey = journey_repo.get_active_journey_for_account(account_id)
        else:
            attributes = payload.get("attributes", {}) or {}
            plan_type = attributes.get("plan_type")
            if plan_type is None:
                raise InvalidEventError("OrderCompleted requires attributes.plan_type to enroll a new line")
            journey = enroll_line_on_order_completed(
                session,
                account_id=account_id,
                customer_id=payload["customer_id"],
                line_id=line_id,
                plan_type=plan_type,
                number_port_requested=bool(attributes.get("number_port_requested", False)),
                occurred_at=occurred_at,
            )
    else:
        journey = journey_repo.get_active_journey_for_account(account_id)

    if event_type in EVENTS_REQUIRING_EXISTING_JOURNEY:
        if journey is None:
            event_repo.save_dead_letter(
                event_id=event_id,
                event_type=event_type,
                account_id=account_id,
                line_id=line_id,
                reason="UNKNOWN_ACCOUNT",
                raw_payload=_json_safe(payload),
            )
            return IngestResult(event_id=event_id, outcome="dead_lettered", dead_letter_reason="UNKNOWN_ACCOUNT")

        if line_id is not None:
            line_state = journey_repo.get_line_onboarding_state(line_id)
            if line_state is None or line_state.journey_id != journey.journey_id:
                event_repo.save_dead_letter(
                    event_id=event_id,
                    event_type=event_type,
                    account_id=account_id,
                    line_id=line_id,
                    reason="UNKNOWN_LINE",
                    raw_payload=_json_safe(payload),
                )
                return IngestResult(event_id=event_id, outcome="dead_lettered", dead_letter_reason="UNKNOWN_LINE")

    event_repo.save_domain_event(
        event_id=event_id,
        event_type=event_type,
        customer_id=payload["customer_id"],
        account_id=account_id,
        line_id=line_id,
        journey_id=journey.journey_id if journey else payload.get("journey_id"),
        occurred_at=occurred_at,
        source=payload["source"],
        correlation_id=payload["correlation_id"],
        attributes=payload.get("attributes", {}),
    )
    event_repo.mark_processed(event_id)

    if journey is not None:
        apply_event_to_journey(
            session,
            journey_id=journey.journey_id,
            line_id=line_id,
            event_id=event_id,
            event_type=event_type,
            occurred_at=occurred_at,
            correlation_id=payload["correlation_id"],
        )

        # Downstream health/NBA recomputation hook (T034): every event that
        # reaches an existing journey may affect friction/health/NBA even
        # when it doesn't change an ActivityInstance (e.g. HelpArticleViewed).
        affected_line_ids = [line_id] if line_id is not None else [
            state.line_id for state in journey_repo.list_line_states_for_journey(journey.journey_id)
        ]
        for affected_line_id in affected_line_ids:
            recompute_line(session, journey.journey_id, affected_line_id, journey.started_at, as_of=occurred_at)

    return IngestResult(event_id=event_id, outcome="applied")


def _json_safe(payload: dict) -> dict:
    safe = dict(payload)
    occurred_at = safe.get("occurred_at")
    if isinstance(occurred_at, datetime):
        safe["occurred_at"] = occurred_at.isoformat()
    return safe
