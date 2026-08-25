"""US2 AC9: no proactive outreach is delivered to an opted-out customer,
regardless of urgency, and the suppression is recorded (not the cap)."""

from concierge.decisioning.recompute import allocate_outreach_for_journey
from concierge.persistence.repositories import ConsentRepository


def test_opted_out_customer_scenario_seed_is_opted_out(db_session):
    from concierge.journey.scenario_loader import load_scenario

    result = load_scenario(db_session, "customer-opt-out")
    consent = ConsentRepository(db_session).get_consent(result["customer_id"])
    assert consent is not None
    assert consent.opted_out is True


def test_opted_out_customer_gets_no_delivered_outreach(db_session):
    from concierge.journey.scenario_loader import load_scenario

    result = load_scenario(db_session, "customer-opt-out")
    db_session.commit()

    decisions = allocate_outreach_for_journey(
        db_session, result["customer_id"], result["journey_id"], result["line_ids"]
    )
    assert decisions, "expected at least one candidate to evaluate (recommended-activity gaps are open)"
    assert all(d.status == "SUPPRESSED" for d in decisions)
    assert all(d.suppression_reason == "OPTED_OUT" for d in decisions)


def test_opting_back_in_allows_delivery(db_session):
    from concierge.journey.scenario_loader import load_scenario

    result = load_scenario(db_session, "customer-opt-out")
    db_session.commit()

    ConsentRepository(db_session).set_opted_out(result["customer_id"], False)
    db_session.commit()

    from datetime import datetime, timezone

    noon = datetime.now(timezone.utc).replace(hour=12, minute=0, second=0, microsecond=0)
    decisions = allocate_outreach_for_journey(
        db_session, result["customer_id"], result["journey_id"], result["line_ids"], as_of=noon
    )
    assert any(d.status == "DELIVERED" for d in decisions)
