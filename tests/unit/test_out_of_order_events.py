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
    repo.create_activity_instance(journey.journey_id, "line-1", "NETWORK_VALIDATION", "REQUIRED", "NOT_STARTED")
    session.flush()
    return journey.journey_id


def _event(event_id: str, event_type: str, occurred_at: datetime) -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "customer_id": "cust-1",
        "account_id": "acct-1",
        "line_id": "line-1",
        "occurred_at": occurred_at.isoformat(),
        "source": "test",
        "correlation_id": "corr-1",
        "attributes": {},
    }


def test_failed_event_arriving_after_completed_does_not_regress_status(db_session):
    journey_id = _seed_journey_with_line(db_session)
    t0 = datetime.now(timezone.utc)

    ingest_event(db_session, _event("evt-1", "DeviceActivationStarted", t0))
    ingest_event(db_session, _event("evt-2", "DeviceActivationCompleted", t0 + timedelta(minutes=1)))

    repo = JourneyRepository(db_session)
    instance = repo.get_activity_instance(journey_id, "line-1", "SIM_ESIM_ACTIVATION")
    assert instance.status == "COMPLETED"

    # A FAILED event for an earlier point in time, delivered out of order
    # (received after COMPLETED was already applied).
    ingest_event(db_session, _event("evt-3", "DeviceActivationFailed", t0 + timedelta(seconds=30)))

    instance_after = repo.get_activity_instance(journey_id, "line-1", "SIM_ESIM_ACTIVATION")
    assert instance_after.status == "COMPLETED"


def test_state_transition_log_records_only_actual_changes(db_session):
    journey_id = _seed_journey_with_line(db_session)
    t0 = datetime.now(timezone.utc)

    ingest_event(db_session, _event("evt-1", "DeviceActivationStarted", t0))
    ingest_event(db_session, _event("evt-2", "DeviceActivationCompleted", t0 + timedelta(minutes=1)))
    # Out-of-order FAILED after COMPLETED must not produce a spurious transition log entry.
    ingest_event(db_session, _event("evt-3", "DeviceActivationFailed", t0 + timedelta(seconds=30)))

    from concierge.persistence.event_models import StateTransitionLog

    entries = (
        db_session.query(StateTransitionLog)
        .filter_by(journey_id=journey_id, entity_type="ACTIVITY_INSTANCE")
        .all()
    )
    # SIM_ESIM_ACTIVATION + NETWORK_VALIDATION each transition twice (Started, Completed) = 4 entries.
    assert len(entries) == 4
