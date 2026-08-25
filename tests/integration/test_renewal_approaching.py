"""US3 AC5: prepaid-renewal-approaching scenario — renewal-readiness fields
are correct, and the auto-recharge gap is reflected in health/NBA."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_renewal_approaching_scenario_billing_endpoint(api_client):
    scenario = api_client.post("/api/demo/scenarios/prepaid-renewal-approaching/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    line_id = scenario["line_ids"][0]

    r = api_client.get(f"/api/journeys/{scenario['journey_id']}/billing", params={"line_id": line_id}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["plan_type"] == "PREPAID"
    assert body["postpaid_estimate"] is None
    renewal = body["prepaid_renewal"]
    assert renewal["balance"] == 12.5
    assert renewal["auto_recharge_enabled"] is False
    assert renewal["renewal_ready"] is False
    assert body["explanation"]


def test_renewal_approaching_scenario_also_shows_auto_recharge_gap_in_nba(api_client):
    """The billing view and the NBA/health view are two lenses on the same
    underlying gap — both should be consistent."""
    scenario = api_client.post("/api/demo/scenarios/prepaid-renewal-approaching/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]

    billing = api_client.get(
        f"/api/journeys/{journey_id}/billing", params={"line_id": scenario["line_ids"][0]}, headers=headers
    ).json()
    assert billing["prepaid_renewal"]["auto_recharge_enabled"] is False

    nba = api_client.get(f"/api/journeys/{journey_id}/recommendation", headers=headers).json()
    assert nba[0]["action_code"] == "AUTOPAY_AUTO_RECHARGE_GAP"

    health = api_client.get(f"/api/journeys/{journey_id}/health", headers=headers).json()
    assert any(rc["code"] == "AUTOPAY_AUTO_RECHARGE_INCOMPLETE" for rc in health["lines"][0]["reason_codes"])
