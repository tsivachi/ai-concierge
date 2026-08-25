"""FR-022/FR-023: ConciergeContext must be assembled entirely from real
provider/state-sourced fields — no LLM-invented values are possible by
construction, since the dataclass only ever holds what assemble_context
actually queried."""

from datetime import datetime, timedelta, timezone

from concierge.conversation.context import ConciergeContext, assemble_context
from concierge.decisioning.recompute import recompute_line
from concierge.persistence.repositories import JourneyRepository


def _seed(session):
    repo = JourneyRepository(session)
    repo.create_account("acct-1", "cust-1")
    started_at = datetime.now(timezone.utc) - timedelta(days=2)
    journey = repo.create_journey("acct-1", started_at, started_at + timedelta(days=30))
    repo.create_line("line-1", "acct-1", "POSTPAID")
    repo.create_line_onboarding_state("line-1", journey.journey_id, "POSTPAID")
    repo.create_activity_instance(journey.journey_id, "line-1", "SIM_ESIM_ACTIVATION", "REQUIRED", "FAILED")
    repo.create_activity_instance(journey.journey_id, "line-1", "ACCOUNT_SECURITY", "REQUIRED", "NOT_STARTED")
    session.flush()
    return journey


def test_context_fields_are_all_dataclass_typed_no_arbitrary_data(db_session):
    journey = _seed(db_session)
    recompute_line(db_session, journey.journey_id, "line-1", journey.started_at)

    context = assemble_context(db_session, journey.journey_id, "line-1")
    assert isinstance(context, ConciergeContext)
    # frozen dataclass -> attempting to add an arbitrary field is impossible.
    import dataclasses

    field_names = {f.name for f in dataclasses.fields(context)}
    assert field_names == {
        "customer_id",
        "account_id",
        "journey_id",
        "line_id",
        "plan_type",
        "journey_day",
        "activities",
        "current_nba",
        "health",
        "billing_facts",
        "recent_support_context",
    }


def test_context_reflects_actual_seeded_state(db_session):
    journey = _seed(db_session)
    recompute_line(db_session, journey.journey_id, "line-1", journey.started_at)

    context = assemble_context(db_session, journey.journey_id, "line-1")
    assert context.customer_id == "cust-1"
    assert context.account_id == "acct-1"
    assert context.plan_type == "POSTPAID"
    assert context.journey_day >= 2
    assert context.current_nba is not None
    assert context.current_nba.action_code == "ACTIVATION_FAILURE"
    assert context.health is not None
    assert context.health.score < 100


def test_context_billing_facts_is_none_when_billing_not_wired(db_session):
    journey = _seed(db_session)
    recompute_line(db_session, journey.journey_id, "line-1", journey.started_at)
    context = assemble_context(db_session, journey.journey_id, "line-1")
    assert context.billing_facts is None


def test_context_is_frozen_and_immutable(db_session):
    journey = _seed(db_session)
    recompute_line(db_session, journey.journey_id, "line-1", journey.started_at)
    context = assemble_context(db_session, journey.journey_id, "line-1")

    import dataclasses

    with_error = False
    try:
        context.customer_id = "someone-else"
    except dataclasses.FrozenInstanceError:
        with_error = True
    assert with_error
