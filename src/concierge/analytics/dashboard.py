"""Aggregate dashboard metrics (FR-035). Pure counting/aggregation over
already-persisted journey/outreach/escalation state — no new business rules,
just read models over what decisioning already computed."""

from dataclasses import dataclass

from sqlalchemy.orm import Session

from concierge.persistence.decision_models import EscalationCase, OutreachAttempt
from concierge.persistence.event_models import DomainEvent
from concierge.persistence.models import Account, AccountJourney, LineOnboardingState


@dataclass(frozen=True)
class EngagementCounts:
    proactive_contacts_delivered: int
    chat_sessions: int


@dataclass(frozen=True)
class DashboardMetrics:
    enrolled_customers: int
    engagement: EngagementCounts
    onboarding_completion_rate: float
    digital_resolutions: int
    escalations: int


def compute_dashboard_metrics(session: Session) -> DashboardMetrics:
    enrolled_customers = session.query(Account).count()

    total_lines = session.query(LineOnboardingState).count()
    complete_lines = session.query(LineOnboardingState).filter_by(status="COMPLETE").count()
    onboarding_completion_rate = round(complete_lines / total_lines, 4) if total_lines else 0.0

    proactive_contacts_delivered = session.query(OutreachAttempt).filter_by(status="DELIVERED").count()
    chat_sessions = session.query(DomainEvent.correlation_id).filter(DomainEvent.event_type == "ChatStarted").count()

    total_escalations = session.query(EscalationCase).count()
    resolved_or_closed = (
        session.query(EscalationCase).filter(EscalationCase.status.in_(("RESOLVED", "CLOSED"))).count()
    )
    # "Digital resolutions" = issues handled without ever needing an
    # escalation, approximated here as delivered outreach that didn't lead
    # to an escalation, plus escalations the concierge itself resolved.
    digital_resolutions = max(0, proactive_contacts_delivered - total_escalations) + resolved_or_closed

    return DashboardMetrics(
        enrolled_customers=enrolled_customers,
        engagement=EngagementCounts(
            proactive_contacts_delivered=proactive_contacts_delivered, chat_sessions=chat_sessions
        ),
        onboarding_completion_rate=onboarding_completion_rate,
        digital_resolutions=digital_resolutions,
        escalations=total_escalations,
    )


def count_active_journeys(session: Session) -> int:
    return session.query(AccountJourney).filter_by(status="ACTIVE").count()
