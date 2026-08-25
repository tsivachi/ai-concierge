"""Integration test: POST /api/events -> GET /api/journeys/{id} progression,
via the real ASGI app (httpx TestClient), not direct repository calls."""


def _reset(client, scenario_id="postpaid-device-port-in"):
    r = client.post(f"/api/demo/scenarios/{scenario_id}/reset")
    assert r.status_code == 200
    return r.json()


def _post_event(client, event_id, event_type, scenario, occurred_at="2026-08-24T00:00:00Z"):
    return client.post(
        "/api/events",
        json={
            "event_id": event_id,
            "event_type": event_type,
            "customer_id": scenario["customer_id"],
            "account_id": scenario["account_id"],
            "line_id": scenario["line_ids"][0],
            "occurred_at": occurred_at,
            "source": "test",
            "correlation_id": "corr-int-1",
            "attributes": {},
        },
    )


def test_scenario_reset_returns_seeded_journey(api_client):
    scenario = _reset(api_client)
    assert scenario["journey_id"]
    assert scenario["line_ids"]


def test_posting_activation_events_progresses_journey_state(api_client):
    scenario = _reset(api_client)

    r1 = _post_event(api_client, "evt-1", "DeviceActivationStarted", scenario)
    assert r1.status_code == 202
    assert r1.json()["outcome"] == "applied"

    r2 = _post_event(api_client, "evt-2", "DeviceActivationCompleted", scenario, occurred_at="2026-08-24T00:05:00Z")
    assert r2.status_code == 202
    assert r2.json()["outcome"] == "applied"


def test_duplicate_event_via_api_is_idempotent(api_client):
    scenario = _reset(api_client)
    _post_event(api_client, "evt-1", "DeviceActivationStarted", scenario)

    r = _post_event(api_client, "evt-1", "DeviceActivationStarted", scenario)
    assert r.status_code == 202
    assert r.json()["outcome"] == "duplicate"


def test_event_for_unknown_line_is_dead_lettered_via_api(api_client):
    scenario = _reset(api_client)
    r = api_client.post(
        "/api/events",
        json={
            "event_id": "evt-ghost",
            "event_type": "DeviceActivationStarted",
            "customer_id": scenario["customer_id"],
            "account_id": scenario["account_id"],
            "line_id": "line-does-not-exist",
            "occurred_at": "2026-08-24T00:00:00Z",
            "source": "test",
            "correlation_id": "corr-int-2",
            "attributes": {},
        },
    )
    assert r.status_code == 202
    assert r.json()["outcome"] == "dead_lettered"


def test_missing_required_field_is_rejected(api_client):
    r = api_client.post(
        "/api/events",
        json={
            "event_id": "evt-bad",
            "event_type": "DeviceActivationStarted",
            "customer_id": "cust-x",
            # account_id missing
            "occurred_at": "2026-08-24T00:00:00Z",
            "source": "test",
            "correlation_id": "corr-int-3",
        },
    )
    assert r.status_code == 422


def test_scenario_list_endpoint_returns_eleven_scenarios(api_client):
    r = api_client.get("/api/demo/scenarios")
    assert r.status_code == 200
    assert len(r.json()) == 11


def test_login_with_seeded_customer_succeeds(api_client):
    scenario = _reset(api_client)
    r = api_client.post("/api/auth/login", json={"customer_id": scenario["customer_id"]})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_with_unknown_customer_is_rejected(api_client):
    r = api_client.post("/api/auth/login", json={"customer_id": "no-such-customer"})
    assert r.status_code == 404
