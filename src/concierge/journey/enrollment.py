"""Journey enrollment on OrderCompleted (FR-001, FR-002, FR-003). At most one
active AccountJourney per account (spec.md Assumptions, Clarifications): a
second qualifying order for an account that already has one attaches its
line(s) to the existing journey instead of starting a new one.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from concierge.domain.enums import ActivityScope, PlanType
from concierge.journey.activity_catalog import CONDITIONALLY_APPLICABLE_ACTIVITY_CODES, activities_for_plan_type
from concierge.persistence.models import AccountJourney
from concierge.persistence.repositories import JourneyRepository

JOURNEY_LENGTH_DAYS = 30


def instantiate_activities_for_line(
    journey_repo: JourneyRepository,
    journey_id: str,
    line_id: str,
    plan_type: PlanType,
    number_port_requested: bool,
) -> None:
    """Creates every ActivityInstance the plan-type catalog defines for this
    line (FR-004): line-scoped activities under this line_id, account-scoped
    activities once per journey. NUMBER_TRANSFER is set NOT_APPLICABLE when
    no port was requested (FR-043/spec.md Edge Cases)."""
    for definition in activities_for_plan_type(plan_type):
        applicable = True
        if definition.activity_code in CONDITIONALLY_APPLICABLE_ACTIVITY_CODES and not number_port_requested:
            applicable = False

        status = "NOT_APPLICABLE" if not applicable else "NOT_STARTED"
        target_line_id = line_id if definition.scope == ActivityScope.LINE else None

        # ACCOUNT-scoped activities are shared across lines; only instantiate once per journey.
        if definition.scope == ActivityScope.ACCOUNT:
            existing = journey_repo.get_activity_instance(journey_id, None, definition.activity_code)
            if existing is not None:
                continue

        journey_repo.create_activity_instance(
            journey_id=journey_id,
            line_id=target_line_id,
            activity_code=definition.activity_code,
            requirement_class=definition.requirement_class.value,
            status=status,
        )


def enroll_line_on_order_completed(
    session: Session,
    account_id: str,
    customer_id: str,
    line_id: str,
    plan_type: str,
    number_port_requested: bool,
    occurred_at: datetime,
) -> AccountJourney:
    """Handles one line's OrderCompleted: creates the account if unseen,
    attaches to the account's existing ACTIVE journey or creates a new one
    (FR-001), and instantiates this line's activity catalog (FR-002, FR-003).
    Idempotent by line_id — an OrderCompleted for a line that's already
    enrolled is a safe no-op (on top of FR-008's event_id-level idempotency,
    which already prevents literal duplicate events from reaching here)."""
    journey_repo = JourneyRepository(session)

    journey_repo.get_or_create_account(account_id, customer_id)

    existing_line = journey_repo.get_line(line_id)
    if existing_line is not None:
        journey = journey_repo.get_active_journey_for_account(account_id)
        if journey is not None:
            return journey

    journey = journey_repo.get_active_journey_for_account(account_id)
    if journey is None:
        expires_at = occurred_at + timedelta(days=JOURNEY_LENGTH_DAYS)
        journey = journey_repo.create_journey(account_id, occurred_at, expires_at)

    if existing_line is None:
        plan_type_enum = PlanType(plan_type)
        journey_repo.create_line(line_id, account_id, plan_type_enum.value)
        journey_repo.create_line_onboarding_state(line_id, journey.journey_id, plan_type_enum.value)
        instantiate_activities_for_line(journey_repo, journey.journey_id, line_id, plan_type_enum, number_port_requested)
        session.flush()

    return journey
