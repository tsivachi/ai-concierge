"""US3: no app-adoption NBA before the day-3 threshold, present after, and
cleared once MobileAppDownloaded arrives."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_app_adoption_gap_scenario_surfaces_app_gap_nba(api_client):
    scenario = api_client.post("/api/demo/scenarios/app-adoption-gap-day3/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]

    nba = api_client.get(f"/api/journeys/{journey_id}/recommendation", headers=headers).json()
    assert nba[0]["action_code"] == "APP_GAP"


def test_mobile_app_downloaded_clears_the_app_gap_nba(api_client):
    scenario = api_client.post("/api/demo/scenarios/app-adoption-gap-day3/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]
    line_id = scenario["line_ids"][0]

    r = api_client.post(
        "/api/events",
        json={
            "event_id": "evt-app-downloaded",
            "event_type": "MobileAppDownloaded",
            "customer_id": scenario["customer_id"],
            "account_id": scenario["account_id"],
            "line_id": line_id,
            "occurred_at": "2026-08-24T12:00:00Z",
            "source": "test",
            "correlation_id": "corr-app-1",
            "attributes": {},
        },
    )
    assert r.status_code == 202

    nba = api_client.get(f"/api/journeys/{journey_id}/recommendation", headers=headers).json()
    assert not any(a["action_code"] == "APP_GAP" for a in nba)

    health = api_client.get(f"/api/journeys/{journey_id}/health", headers=headers).json()
    assert not any(rc["code"] == "APP_NOT_ADOPTED" for rc in health["lines"][0]["reason_codes"])
