"""FR-028: an escalation case must contain enough context that a human agent
never needs the customer to repeat anything already known to the system."""

from datetime import datetime, timedelta, timezone

from concierge.decisioning.escalation import create_escalation_case, resolve_escalation_case, close_escalation_case
from concierge.decisioning.models import ActivitySnapshot
from concierge.domain.enums import ActivityStatus, RequirementClass
from concierge.persistence.repositories import EventRepository, JourneyRepository


def _seed_with_failed_activation(session):
    journey_repo = JourneyRepository(session)
    journey_repo.create_account("acct-1", "cust-1")
    started_at = datetime.now(timezone.utc) - timedelta(days=1)
    journey = journey_repo.create_journey("acct-1", started_at, started_at + timedelta(days=30))
    journey_repo.create_line("line-1", "acct-1", "POSTPAID")
    journey_repo.create_line_onboarding_state("line-1", journey.journey_id, "POSTPAID")
    session.flush()

    event_repo = EventRepository(session)
    event_repo.save_domain_event(
        event_id="evt-1",
        event_type="DeviceActivationFailed",
        customer_id="cust-1",
        account_id="acct-1",
        line_id="line-1",
        journey_id=journey.journey_id,
        occurred_at=datetime.now(timezone.utc),
        source="test",
        correlation_id="corr-1",
        attributes={},
    )
    event_repo.mark_processed("evt-1")
    session.flush()
    return journey


def test_escalation_case_contains_every_required_field(db_session):
    journey = _seed_with_failed_activation(db_session)
    activities = [ActivitySnapshot("SIM_ESIM_ACTIVATION", RequirementClass.REQUIRED, ActivityStatus.FAILED)]

    case = create_escalation_case(
        db_session,
        journey_id=journey.journey_id,
        line_id="line-1",
        reason="UNRESOLVED_ACTIVATION_OR_PORT",
        activities=activities,
        related_action_code="ACTIVATION_FAILURE",
        relevant_event_types=("DeviceActivationFailed",),
        attempted_action_ids=["ACTIVATION_FAILURE"],
        conversation_summary="Customer reported activation keeps failing.",
        health={"score": 70, "band": "YELLOW"},
        nba={"action_code": "ACTIVATION_FAILURE"},
    )

    assert case.case_id
    assert case.journey_id == journey.journey_id
    assert case.line_id == "line-1"
    assert case.reason == "UNRESOLVED_ACTIVATION_OR_PORT"
    assert case.priority == 100
    assert case.related_action_code == "ACTIVATION_FAILURE"
    assert case.journey_snapshot["activities"]
    assert case.journey_snapshot["health"] == {"score": 70, "band": "YELLOW"}
    assert case.journey_snapshot["current_nba"] == {"action_code": "ACTIVATION_FAILURE"}
    assert "evt-1" in case.relevant_event_ids
    assert case.attempted_action_ids == ["ACTIVATION_FAILURE"]
    assert case.conversation_summary == "Customer reported activation keeps failing."
    assert case.status == "OPEN"
    assert case.created_at is not None
    assert case.resolved_at is None


def test_escalation_case_without_relevant_events_still_has_empty_list_not_none(db_session):
    journey = _seed_with_failed_activation(db_session)
    case = create_escalation_case(
        db_session,
        journey_id=journey.journey_id,
        line_id="line-1",
        reason="EXPLICIT_REQUEST",
        activities=[],
    )
    assert case.relevant_event_ids == []
    assert case.attempted_action_ids == []


def test_resolve_escalation_case_sets_status_and_timestamp(db_session):
    journey = _seed_with_failed_activation(db_session)
    case = create_escalation_case(
        db_session, journey_id=journey.journey_id, line_id="line-1", reason="EXPLICIT_REQUEST", activities=[]
    )
    resolved = resolve_escalation_case(db_session, case.case_id)
    assert resolved.status == "RESOLVED"
    assert resolved.resolved_at is not None


def test_close_escalation_case_sets_status_and_timestamp(db_session):
    journey = _seed_with_failed_activation(db_session)
    case = create_escalation_case(
        db_session, journey_id=journey.journey_id, line_id="line-1", reason="EXPLICIT_REQUEST", activities=[]
    )
    closed = close_escalation_case(db_session, case.case_id)
    assert closed.status == "CLOSED"
    assert closed.resolved_at is not None


def test_resolving_unknown_case_returns_none(db_session):
    assert resolve_escalation_case(db_session, "does-not-exist") is None
