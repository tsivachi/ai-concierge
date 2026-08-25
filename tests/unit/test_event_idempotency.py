from datetime import datetime, timedelta, timezone

from concierge.events.ingestion import ingest_event
from concierge.persistence.repositories import JourneyRepository


def _seed_journey_with_line(session):
    repo = JourneyRepository(session)
    repo.create_account("acct-1", "cust-1")
    now = datetime.now(timezone.utc)
    journey = repo.create_journey("acct-1", now, now + timedelta(days=30))
    repo.create_line("line-1", "acct-1", "POSTPAID")
    repo.create_line_onboarding_state("line-1", journey.journey_id, "POSTPAID")
    repo.create_activity_instance(journey.journey_id, "line-1", "SIM_ESIM_ACTIVATION", "REQUIRED", "NOT_STARTED")
    session.flush()
    return journey.journey_id


def _event(event_id: str, event_type: str, line_id: str = "line-1") -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "customer_id": "cust-1",
        "account_id": "acct-1",
        "line_id": line_id,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "source": "test",
        "correlation_id": "corr-1",
        "attributes": {},
    }


def test_first_delivery_is_applied(db_session):
    _seed_journey_with_line(db_session)
    result = ingest_event(db_session, _event("evt-1", "DeviceActivationStarted"))
    assert result.outcome == "applied"


def test_duplicate_event_id_is_a_safe_no_op(db_session):
    journey_id = _seed_journey_with_line(db_session)
    ingest_event(db_session, _event("evt-1", "DeviceActivationStarted"))

    repo = JourneyRepository(db_session)
    instance_before = repo.get_activity_instance(journey_id, "line-1", "SIM_ESIM_ACTIVATION")
    status_before = instance_before.status

    result = ingest_event(db_session, _event("evt-1", "DeviceActivationStarted"))

    instance_after = repo.get_activity_instance(journey_id, "line-1", "SIM_ESIM_ACTIVATION")
    assert result.outcome == "duplicate"
    assert instance_after.status == status_before


def test_replaying_an_event_produces_no_additional_state_change(db_session):
    """SC-005: replaying a previously processed event produces no observable
    change in journey/activity/health/NBA state."""
    journey_id = _seed_journey_with_line(db_session)
    ingest_event(db_session, _event("evt-1", "DeviceActivationStarted"))
    ingest_event(db_session, _event("evt-2", "DeviceActivationCompleted"))

    repo = JourneyRepository(db_session)
    instance = repo.get_activity_instance(journey_id, "line-1", "SIM_ESIM_ACTIVATION")
    assert instance.status.value == "COMPLETED"

    # Replay the first event again — must not resurrect IN_PROGRESS.
    ingest_event(db_session, _event("evt-1", "DeviceActivationStarted"))
    instance_after = repo.get_activity_instance(journey_id, "line-1", "SIM_ESIM_ACTIVATION")
    assert instance_after.status.value == "COMPLETED"
