from datetime import datetime, timedelta, timezone

from concierge.events.ingestion import ingest_event
from concierge.persistence.repositories import EventRepository, JourneyRepository


def _seed_journey_with_line(session, account_id="acct-1", customer_id="cust-1", line_id="line-1"):
    repo = JourneyRepository(session)
    repo.create_account(account_id, customer_id)
    now = datetime.now(timezone.utc)
    journey = repo.create_journey(account_id, now, now + timedelta(days=30))
    repo.create_line(line_id, account_id, "POSTPAID")
    repo.create_line_onboarding_state(line_id, journey.journey_id, "POSTPAID")
    repo.create_activity_instance(journey.journey_id, line_id, "SIM_ESIM_ACTIVATION", "REQUIRED", "NOT_STARTED")
    session.flush()
    return journey.journey_id


def _event(event_id: str, event_type: str, account_id: str, line_id: str | None, customer_id="cust-1") -> dict:
    return {
        "event_id": event_id,
        "event_type": event_type,
        "customer_id": customer_id,
        "account_id": account_id,
        "line_id": line_id,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "source": "test",
        "correlation_id": "corr-1",
        "attributes": {},
    }


def test_event_for_unknown_account_is_dead_lettered_without_state_change(db_session):
    result = ingest_event(
        db_session, _event("evt-1", "DeviceActivationStarted", "ghost-account", None, customer_id="ghost")
    )
    assert result.outcome == "dead_lettered"
    assert result.dead_letter_reason == "UNKNOWN_ACCOUNT"


def test_dead_lettered_event_is_not_marked_processed(db_session):
    ingest_event(db_session, _event("evt-1", "DeviceActivationStarted", "ghost-account", None, customer_id="ghost"))
    event_repo = EventRepository(db_session)
    assert event_repo.is_processed("evt-1") is False


def test_event_for_unknown_line_on_a_known_account_is_dead_lettered(db_session):
    _seed_journey_with_line(db_session)
    result = ingest_event(db_session, _event("evt-2", "DeviceActivationStarted", "acct-1", "ghost-line"))
    assert result.outcome == "dead_lettered"
    assert result.dead_letter_reason == "UNKNOWN_LINE"


def test_resubmission_after_entity_exists_is_processed_normally(db_session):
    # First delivery: account doesn't exist yet -> dead-lettered.
    result1 = ingest_event(
        db_session, _event("evt-3", "DeviceActivationStarted", "acct-2", "line-2", customer_id="cust-2")
    )
    assert result1.outcome == "dead_lettered"

    # The account/journey/line now come into existence (e.g. via OrderCompleted + scenario setup).
    _seed_journey_with_line(db_session, account_id="acct-2", customer_id="cust-2", line_id="line-2")

    # The *same* event_id, resubmitted, is processed normally — it never
    # reached ProcessedEvent the first time.
    result2 = ingest_event(
        db_session, _event("evt-3", "DeviceActivationStarted", "acct-2", "line-2", customer_id="cust-2")
    )
    assert result2.outcome == "applied"


def test_order_completed_enrolls_a_brand_new_line_rather_than_dead_lettering(db_session):
    """OrderCompleted's job is to create the journey (journey/enrollment.py,
    FR-001) — it must never be dead-lettered just because no journey exists
    yet, since that's precisely the event that creates one."""
    event = _event("evt-4", "OrderCompleted", "brand-new-account", "line-new-1", customer_id="new-cust")
    event["attributes"] = {"plan_type": "POSTPAID", "number_port_requested": False}

    result = ingest_event(db_session, event)

    assert result.outcome == "applied"
    journey_repo = JourneyRepository(db_session)
    journey = journey_repo.get_active_journey_for_account("brand-new-account")
    assert journey is not None
    line_state = journey_repo.get_line_onboarding_state("line-new-1")
    assert line_state is not None
    assert line_state.journey_id == journey.journey_id
