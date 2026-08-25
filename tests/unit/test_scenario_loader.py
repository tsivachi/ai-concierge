import pytest

from concierge.journey.scenario_loader import ScenarioNotFoundError, list_scenarios, load_scenario
from concierge.persistence.repositories import DecisionRepository, EventRepository, JourneyRepository

ALL_SCENARIO_IDS = {
    "postpaid-device-port-in",
    "prepaid-byod-esim",
    "multi-line-postpaid",
    "repeated-activation-failure",
    "delayed-failed-port",
    "app-adoption-gap-day3",
    "postpaid-first-bill-day21",
    "prepaid-renewal-approaching",
    "contextual-troubleshooting",
    "human-escalation-with-context",
    "customer-opt-out",
}


def test_list_scenarios_returns_all_eleven_curated_scenarios():
    ids = {s["scenario_id"] for s in list_scenarios()}
    assert ids == ALL_SCENARIO_IDS


def test_loading_unknown_scenario_raises(db_session):
    with pytest.raises(ScenarioNotFoundError):
        load_scenario(db_session, "does-not-exist")


@pytest.mark.parametrize("scenario_id", sorted(ALL_SCENARIO_IDS))
def test_every_scenario_loads_without_error(db_session, scenario_id):
    result = load_scenario(db_session, scenario_id)
    assert result["scenario_id"] == scenario_id
    assert result["journey_id"]
    assert len(result["line_ids"]) >= 1


def test_loading_a_scenario_twice_yields_identical_state_no_residue(db_session):
    """SC-011: each scenario can be independently loaded, exercised, and reset
    without residual state from a prior load affecting the result."""
    first = load_scenario(db_session, "multi-line-postpaid")
    db_session.commit()

    journey_repo = JourneyRepository(db_session)
    first_instances = sorted(
        (i.activity_code, i.line_id, i.status) for i in journey_repo.list_activity_instances_for_journey(
            first["journey_id"]
        )
    )

    second = load_scenario(db_session, "multi-line-postpaid")
    db_session.commit()

    second_instances = sorted(
        (i.activity_code, i.line_id, i.status) for i in journey_repo.list_activity_instances_for_journey(
            second["journey_id"]
        )
    )

    # A fresh journey_id is issued each load, but the resulting activity
    # state shape must be identical (deterministic), and the old journey's
    # rows must be gone (reset, not merged).
    assert [(code, status) for code, _, status in first_instances] == [
        (code, status) for code, _, status in second_instances
    ]
    assert journey_repo.get_journey(first["journey_id"]) is None


def test_reset_clears_prior_scenarios_events_and_decisions(db_session):
    load_scenario(db_session, "repeated-activation-failure")
    db_session.commit()
    event_repo = EventRepository(db_session)
    assert event_repo.get_domain_event("seed-raf-3") is not None

    load_scenario(db_session, "postpaid-device-port-in")
    db_session.commit()

    assert event_repo.get_domain_event("seed-raf-3") is None
    decision_repo = DecisionRepository(db_session)
    assert decision_repo.get_current_nba_for_line("line-repeated-failure-1") is None


def test_number_transfer_not_applicable_when_no_port_requested(db_session):
    result = load_scenario(db_session, "prepaid-byod-esim")
    journey_repo = JourneyRepository(db_session)
    instance = journey_repo.get_activity_instance(result["journey_id"], result["line_ids"][0], "NUMBER_TRANSFER")
    assert instance.status == "NOT_APPLICABLE"


def test_number_transfer_required_when_port_requested(db_session):
    result = load_scenario(db_session, "postpaid-device-port-in")
    journey_repo = JourneyRepository(db_session)
    instance = journey_repo.get_activity_instance(result["journey_id"], result["line_ids"][0], "NUMBER_TRANSFER")
    assert instance.status == "NOT_STARTED"
    assert instance.requirement_class == "REQUIRED"


def test_journey_started_at_is_backdated_per_offset(db_session):
    from datetime import datetime, timezone

    result = load_scenario(db_session, "postpaid-first-bill-day21")
    journey_repo = JourneyRepository(db_session)
    journey = journey_repo.get_journey(result["journey_id"])
    age_days = (datetime.now(timezone.utc) - journey.started_at.replace(tzinfo=timezone.utc)).days
    assert age_days >= 21
