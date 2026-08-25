"""US3 AC4: postpaid-first-bill-day21 scenario — bill estimate is visible
and correctly computed at day 21, explicitly labeled as an estimate."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_first_bill_scenario_billing_endpoint(api_client):
    scenario = api_client.post("/api/demo/scenarios/postpaid-first-bill-day21/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    line_id = scenario["line_ids"][0]

    r = api_client.get(f"/api/journeys/{scenario['journey_id']}/billing", params={"line_id": line_id}, headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["plan_type"] == "POSTPAID"
    assert body["prepaid_renewal"] is None
    estimate = body["postpaid_estimate"]
    assert estimate["total_estimate"] == round(65.0 + 35.0 + 25.0 + 8.5 - 10.0, 2)
    assert "estimate" in estimate["estimate_note"].lower()
    assert body["explanation"]


def test_first_bill_endpoint_requires_authentication(api_client):
    scenario = api_client.post("/api/demo/scenarios/postpaid-first-bill-day21/reset").json()
    r = api_client.get(
        f"/api/journeys/{scenario['journey_id']}/billing", params={"line_id": scenario["line_ids"][0]}
    )
    assert r.status_code == 401


def test_billing_for_a_line_with_no_snapshot_returns_404(api_client):
    scenario = api_client.post("/api/demo/scenarios/postpaid-device-port-in/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    r = api_client.get(
        f"/api/journeys/{scenario['journey_id']}/billing", params={"line_id": scenario["line_ids"][0]}, headers=headers
    )
    assert r.status_code == 404
