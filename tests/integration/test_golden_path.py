"""US1: golden-path walkthrough — reset postpaid-device-port-in, inject
activation/network/security events, and confirm the journey reaches
COMPLETE with no required activity left incomplete."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _post_event(client, event_id, event_type, scenario, occurred_at):
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
            "correlation_id": event_id,
            "attributes": {},
        },
    )


def test_golden_path_reaches_onboarding_complete(api_client):
    scenario = api_client.post("/api/demo/scenarios/postpaid-device-port-in/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]

    journey_before = api_client.get(f"/api/journeys/{journey_id}", headers=headers).json()
    assert journey_before["status"] == "ACTIVE"

    # Complete every required activity: activation, network validation
    # (piggybacks on the same events), number transfer, and account security.
    _post_event(api_client, "gp-1", "DeviceActivationStarted", scenario, "2026-08-24T00:00:00Z")
    _post_event(api_client, "gp-2", "DeviceActivationCompleted", scenario, "2026-08-24T00:05:00Z")
    _post_event(api_client, "gp-3", "NumberTransferRequested", scenario, "2026-08-24T00:06:00Z")
    _post_event(api_client, "gp-4", "NumberTransferCompleted", scenario, "2026-08-24T00:10:00Z")
    _post_event(api_client, "gp-5", "CustomerLoggedIn", scenario, "2026-08-24T00:11:00Z")

    journey_after = api_client.get(f"/api/journeys/{journey_id}", headers=headers).json()
    line = journey_after["lines"][0]
    required = [a for a in line["activities"] + journey_after["account_activities"] if a["requirement_class"] == "REQUIRED"]
    assert all(a["status"] in ("COMPLETED", "NOT_APPLICABLE") for a in required)
    assert line["status"] == "COMPLETE"
    assert journey_after["status"] == "COMPLETE"


def test_recommended_gap_does_not_block_completion(api_client):
    """FR-005: RECOMMENDED/OPTIONAL activities never block completion — only
    the REQUIRED set does."""
    scenario = api_client.post("/api/demo/scenarios/prepaid-byod-esim/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]

    _post_event(api_client, "rg-1", "DeviceActivationStarted", scenario, "2026-08-24T00:00:00Z")
    _post_event(api_client, "rg-2", "DeviceActivationCompleted", scenario, "2026-08-24T00:05:00Z")
    _post_event(api_client, "rg-3", "CustomerLoggedIn", scenario, "2026-08-24T00:06:00Z")
    # Number transfer was NOT_APPLICABLE from the start (no port requested).
    # App adoption (RECOMMENDED) is deliberately left undone.

    journey = api_client.get(f"/api/journeys/{journey_id}", headers=headers).json()
    line = journey["lines"][0]
    app_activity = next(a for a in line["activities"] if a["activity_code"] == "APP_ADOPTION")
    assert app_activity["status"] == "NOT_STARTED"
    assert line["status"] == "COMPLETE"
    assert journey["status"] == "COMPLETE"
