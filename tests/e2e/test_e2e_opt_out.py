"""E2E: customer opt-out. No proactive outreach is delivered regardless of
how urgent the open recommendation is, and the suppression is recorded."""


def test_opt_out_full_walkthrough(api_client):
    scenario = api_client.post("/api/demo/scenarios/customer-opt-out/reset").json()

    from concierge.decisioning.recompute import allocate_outreach_for_journey
    from concierge.persistence.db import get_session_factory
    from concierge.persistence.repositories import ConsentRepository

    session = get_session_factory()()
    try:
        consent = ConsentRepository(session).get_consent(scenario["customer_id"])
        assert consent.opted_out is True

        decisions = allocate_outreach_for_journey(
            session, scenario["customer_id"], scenario["journey_id"], scenario["line_ids"]
        )
        assert decisions
        assert all(d.status == "SUPPRESSED" for d in decisions)
        assert all(d.suppression_reason == "OPTED_OUT" for d in decisions)
        session.commit()
    finally:
        session.close()

    # Even though outreach is suppressed, the journey/health/NBA views
    # themselves are still fully functional for the customer to check manually.
    login = api_client.post("/api/auth/login", json={"customer_id": scenario["customer_id"]}).json()
    headers = {"Authorization": f"Bearer {login['access_token']}"}
    nba = api_client.get(f"/api/journeys/{scenario['journey_id']}/recommendation", headers=headers).json()
    assert nba
