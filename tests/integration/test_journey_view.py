"""GET /api/journeys/{id}: the basic journey view the UI (Phase 10) reads
from. Auth-protected like every other customer-specific journey route."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_journey_view_requires_authentication(api_client):
    scenario = api_client.post("/api/demo/scenarios/postpaid-device-port-in/reset").json()
    r = api_client.get(f"/api/journeys/{scenario['journey_id']}")
    assert r.status_code == 401


def test_journey_view_shows_account_and_line_activities(api_client):
    scenario = api_client.post("/api/demo/scenarios/postpaid-device-port-in/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    r = api_client.get(f"/api/journeys/{scenario['journey_id']}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["journey_id"] == scenario["journey_id"]
    assert body["status"] == "ACTIVE"
    assert body["account_activities"]
    assert len(body["lines"]) == 1
    assert body["lines"][0]["line_id"] == scenario["line_ids"][0]
    assert body["lines"][0]["activities"]


def test_multiline_journey_status_reflects_per_line_progress(api_client):
    scenario = api_client.post("/api/demo/scenarios/multi-line-postpaid/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    r = api_client.get(f"/api/journeys/{scenario['journey_id']}", headers=headers)
    body = r.json()
    assert len(body["lines"]) == 2
    # Account status is not COMPLETE while at least one line still has open required activities.
    assert body["status"] != "COMPLETE"
