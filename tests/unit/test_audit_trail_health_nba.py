"""FR-009 / Constitution Principle VI: StateTransitionLog must cover
HealthScoreRecord and NextBestActionRecord changes, not just ActivityInstance
transitions (closes analyze finding H3)."""

from datetime import datetime, timedelta, timezone

from concierge.decisioning.recompute import recompute_line
from concierge.persistence.event_models import StateTransitionLog
from concierge.persistence.repositories import JourneyRepository


def _seed_journey_with_failed_activation(session):
    repo = JourneyRepository(session)
    repo.create_account("acct-1", "cust-1")
    started_at = datetime.now(timezone.utc) - timedelta(days=1)
    journey = repo.create_journey("acct-1", started_at, started_at + timedelta(days=30))
    repo.create_line("line-1", "acct-1", "POSTPAID")
    repo.create_line_onboarding_state("line-1", journey.journey_id, "POSTPAID")
    repo.create_activity_instance(journey.journey_id, "line-1", "SIM_ESIM_ACTIVATION", "REQUIRED", "FAILED")
    repo.create_activity_instance(journey.journey_id, "line-1", "NETWORK_VALIDATION", "REQUIRED", "NOT_STARTED")
    repo.create_activity_instance(journey.journey_id, "line-1", "ACCOUNT_SECURITY", "REQUIRED", "NOT_STARTED")
    session.flush()
    return journey


def test_recompute_writes_health_score_state_transition_log(db_session):
    journey = _seed_journey_with_failed_activation(db_session)
    recompute_line(db_session, journey.journey_id, "line-1", journey.started_at)

    entries = (
        db_session.query(StateTransitionLog)
        .filter_by(journey_id=journey.journey_id, entity_type="HEALTH_SCORE", line_id="line-1")
        .all()
    )
    assert len(entries) == 1
    assert entries[0].after_state["score"] < 100


def test_recompute_writes_next_best_action_state_transition_log(db_session):
    journey = _seed_journey_with_failed_activation(db_session)
    recompute_line(db_session, journey.journey_id, "line-1", journey.started_at)

    entries = (
        db_session.query(StateTransitionLog)
        .filter_by(journey_id=journey.journey_id, entity_type="NEXT_BEST_ACTION", line_id="line-1")
        .all()
    )
    assert len(entries) == 1
    assert entries[0].after_state["action_code"] == "ACTIVATION_FAILURE"


def test_recompute_twice_logs_before_and_after_state_on_change(db_session):
    journey = _seed_journey_with_failed_activation(db_session)
    recompute_line(db_session, journey.journey_id, "line-1", journey.started_at)

    # Resolve the activation, then recompute again — the health score should
    # change, and the log should capture both the before and after score.
    journey_repo = JourneyRepository(db_session)
    instance = journey_repo.get_activity_instance(journey.journey_id, "line-1", "SIM_ESIM_ACTIVATION")
    instance.status = "COMPLETED"
    db_session.flush()

    recompute_line(db_session, journey.journey_id, "line-1", journey.started_at)

    entries = (
        db_session.query(StateTransitionLog)
        .filter_by(journey_id=journey.journey_id, entity_type="HEALTH_SCORE", line_id="line-1")
        .order_by(StateTransitionLog.occurred_at)
        .all()
    )
    assert len(entries) == 2
    assert entries[1].before_state["score"] == entries[0].after_state["score"]
    assert entries[1].after_state["score"] > entries[1].before_state["score"]
