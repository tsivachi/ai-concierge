"""Assembles a read-only ConciergeContext DTO from the customer's actual
current state (FR-022) — the *only* thing the conversation engine ever hands
to an LLM. The engine never queries persistence beyond this assembly step,
and the LLM never sees anything not already present here (FR-023)."""

from dataclasses import dataclass, field
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from concierge.decisioning.models import ActivitySnapshot
from concierge.domain.enums import ActivityStatus, RequirementClass
from concierge.persistence.event_models import DomainEvent
from concierge.persistence.repositories import DecisionRepository, JourneyRepository

RECENT_SUPPORT_EVENT_TYPES = ("SupportCaseCreated", "ChatStarted", "HelpArticleViewed")


@dataclass(frozen=True)
class NBAContext:
    action_code: str
    priority: int
    reason_codes: list[dict]


@dataclass(frozen=True)
class HealthContext:
    score: int
    band: str
    reason_codes: list[dict]


@dataclass(frozen=True)
class ActivityContext:
    activity_code: str
    status: str
    requirement_class: str


@dataclass(frozen=True)
class ConciergeContext:
    customer_id: str
    account_id: str
    journey_id: str
    line_id: str
    plan_type: str
    journey_day: int
    activities: list[ActivityContext]
    current_nba: NBAContext | None
    health: HealthContext | None
    billing_facts: dict | None  # None: billing/renewal not wired in this MVP slice (Phase 6)
    recent_support_context: list[str] = field(default_factory=list)


def assemble_context(session: Session, journey_id: str, line_id: str, as_of: datetime | None = None) -> ConciergeContext:
    as_of = as_of or datetime.now(timezone.utc)
    journey_repo = JourneyRepository(session)
    decision_repo = DecisionRepository(session)

    journey = journey_repo.get_journey(journey_id)
    account = journey_repo.get_account(journey.account_id)
    line_state = journey_repo.get_line_onboarding_state(line_id)

    started_at = journey.started_at if journey.started_at.tzinfo else journey.started_at.replace(tzinfo=timezone.utc)
    journey_day = (as_of - started_at).days

    activity_rows = journey_repo.list_activity_instances_for_journey(journey_id)
    activities = [
        ActivityContext(activity_code=a.activity_code, status=a.status, requirement_class=a.requirement_class)
        for a in activity_rows
        if a.line_id in (line_id, None)
    ]

    nba_record = decision_repo.get_current_nba_for_line(line_id)
    current_nba = (
        NBAContext(action_code=nba_record.action_code, priority=nba_record.priority, reason_codes=nba_record.reason_codes)
        if nba_record is not None
        else None
    )

    health_record = decision_repo.get_current_health_score(journey_id, line_id)
    health = (
        HealthContext(score=health_record.score, band=health_record.band, reason_codes=health_record.reason_codes)
        if health_record is not None
        else None
    )

    recent_events = (
        session.query(DomainEvent)
        .filter(DomainEvent.journey_id == journey_id, DomainEvent.line_id == line_id)
        .filter(DomainEvent.event_type.in_(RECENT_SUPPORT_EVENT_TYPES))
        .order_by(DomainEvent.occurred_at.desc())
        .limit(5)
        .all()
    )
    recent_support_context = [f"{e.event_type} at {e.occurred_at.isoformat()}" for e in recent_events]

    return ConciergeContext(
        customer_id=account.customer_id,
        account_id=account.account_id,
        journey_id=journey_id,
        line_id=line_id,
        plan_type=line_state.plan_type,
        journey_day=journey_day,
        activities=activities,
        current_nba=current_nba,
        health=health,
        billing_facts=None,
        recent_support_context=recent_support_context,
    )


def activity_snapshots_from_context(context: ConciergeContext) -> list[ActivitySnapshot]:
    """Converts a ConciergeContext's activity view back into the
    ActivitySnapshot shape decisioning/nba.py and escalation.py expect."""
    return [
        ActivitySnapshot(
            activity_code=a.activity_code,
            requirement_class=RequirementClass(a.requirement_class),
            status=ActivityStatus(a.status),
        )
        for a in context.activities
    ]
