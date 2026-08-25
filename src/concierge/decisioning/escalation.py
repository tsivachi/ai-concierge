"""Escalation triggers (FR-027), case creation (FR-028), and lifecycle
(FR-028a). The six trigger detectors are pure/deterministic — whether to
escalate is never delegated to the LLM (Constitution Principle I); only the
final `conversation_summary` field may contain LLM-authored text, and even
that never influences *whether* escalation happens.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from concierge.decisioning.models import ActivitySnapshot
from concierge.domain.enums import ActivityStatus
from concierge.persistence.repositories import DecisionRepository, EventRepository

TWO_ATTEMPT_THRESHOLD = 2

# spec.md Assumptions: deterministic keyword detectors for the two triggers
# that require classifying free text (a request for a human, a billing
# dispute, or a sensitive security concern) — never an LLM judgment call.
EXPLICIT_HUMAN_REQUEST_PHRASES = (
    "talk to a human",
    "speak to a human",
    "speak to a person",
    "speak with a representative",
    "human agent",
    "real person",
    "customer service rep",
    "talk to someone",
    "connect me with an agent",
)

BILLING_DISPUTE_PHRASES = (
    "dispute",
    "wrong charge",
    "charge is wrong",
    "charge is incorrect",
    "incorrect charge",
    "unauthorized charge",
    "overcharged",
    "charged me wrong",
    "billed incorrectly",
    "charged twice",
)

SENSITIVE_SECURITY_PHRASES = (
    "unauthorized",
    "someone else",
    "hacked",
    "fraud",
    "don't recognize this login",
    "didn't authorize",
    "stolen",
    "identity theft",
    "suspicious activity",
    "someone ported",
)

REASON_PRIORITY = {
    "UNRESOLVED_ACTIVATION_OR_PORT": 100,
    "SENSITIVE_ACCOUNT_SECURITY": 90,
    "BILLING_DISPUTE": 80,
    "EXPLICIT_REQUEST": 70,
    "TWO_FAILED_TROUBLESHOOTING": 60,
    "UNSUPPORTED_LOW_CONFIDENCE": 50,
}

_ACTIVATION_OR_PORT_CODES = ("SIM_ESIM_ACTIVATION", "NETWORK_VALIDATION", "NUMBER_TRANSFER")
_ACTIVATION_OR_PORT_ACTION_CODE = {
    "SIM_ESIM_ACTIVATION": "ACTIVATION_FAILURE",
    "NETWORK_VALIDATION": "NETWORK_FAILURE",
    "NUMBER_TRANSFER": "NUMBER_TRANSFER_FAILURE",
}


# -- Pure trigger detectors -------------------------------------------------


def explicit_request_trigger(message: str) -> bool:
    text = message.lower()
    return any(phrase in text for phrase in EXPLICIT_HUMAN_REQUEST_PHRASES)


def billing_dispute_trigger(message: str) -> bool:
    text = message.lower()
    return any(phrase in text for phrase in BILLING_DISPUTE_PHRASES)


def sensitive_security_trigger(message: str) -> bool:
    text = message.lower()
    return any(phrase in text for phrase in SENSITIVE_SECURITY_PHRASES)


def two_failed_troubleshooting_trigger(consecutive_unresolved_count: int) -> bool:
    return consecutive_unresolved_count >= TWO_ATTEMPT_THRESHOLD


def unsupported_low_confidence_trigger(retrieved_source_count: int, requested_unsupported_action: bool) -> bool:
    """FR-027 'unsupported/low-confidence': the concierge found nothing
    relevant in the knowledge base, or the request maps to no supported
    action (spec.md Assumptions)."""
    return requested_unsupported_action or retrieved_source_count == 0


def unresolved_activation_or_port_trigger(activities: list[ActivitySnapshot]) -> str | None:
    """Returns the related NBA action_code if a REQUIRED activation/port
    activity is FAILED, else None."""
    by_code = {a.activity_code: a for a in activities}
    for code in _ACTIVATION_OR_PORT_CODES:
        activity = by_code.get(code)
        if activity is not None and activity.status == ActivityStatus.FAILED:
            return _ACTIVATION_OR_PORT_ACTION_CODE[code]
    return None


# -- Case creation & lifecycle (I/O) ----------------------------------------


def build_journey_snapshot(activities: list[ActivitySnapshot], health: dict | None, nba: dict | None) -> dict:
    return {
        "activities": [
            {"activity_code": a.activity_code, "status": a.status, "requirement_class": a.requirement_class}
            for a in activities
        ],
        "health": health,
        "current_nba": nba,
    }


def create_escalation_case(
    session: Session,
    journey_id: str,
    line_id: str | None,
    reason: str,
    activities: list[ActivitySnapshot],
    related_action_code: str | None = None,
    relevant_event_types: tuple[str, ...] = (),
    attempted_action_ids: list[str] | None = None,
    conversation_summary: str | None = None,
    health: dict | None = None,
    nba: dict | None = None,
):
    decision_repo = DecisionRepository(session)
    event_repo = EventRepository(session)

    relevant_event_ids: list[str] = []
    if relevant_event_types:
        from concierge.persistence.event_models import DomainEvent

        rows = (
            session.query(DomainEvent)
            .filter(DomainEvent.journey_id == journey_id, DomainEvent.line_id == line_id)
            .filter(DomainEvent.event_type.in_(relevant_event_types))
            .order_by(DomainEvent.occurred_at.desc())
            .limit(10)
            .all()
        )
        relevant_event_ids = [r.event_id for r in rows]

    snapshot = build_journey_snapshot(activities, health, nba)

    return decision_repo.save_escalation_case(
        journey_id=journey_id,
        line_id=line_id,
        reason=reason,
        priority=REASON_PRIORITY[reason],
        related_action_code=related_action_code,
        journey_snapshot=snapshot,
        relevant_event_ids=relevant_event_ids,
        attempted_action_ids=attempted_action_ids or [],
        conversation_summary=conversation_summary,
    )


def resolve_escalation_case(session: Session, case_id: str):
    decision_repo = DecisionRepository(session)
    case = decision_repo.get_escalation_case(case_id)
    if case is None:
        return None
    case.status = "RESOLVED"
    case.resolved_at = datetime.now(timezone.utc)
    session.flush()
    return case


def close_escalation_case(session: Session, case_id: str):
    decision_repo = DecisionRepository(session)
    case = decision_repo.get_escalation_case(case_id)
    if case is None:
        return None
    case.status = "CLOSED"
    case.resolved_at = datetime.now(timezone.utc)
    session.flush()
    return case
