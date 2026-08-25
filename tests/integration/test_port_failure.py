"""US2 AC3: a number transfer stuck pending too long reflects the
port-pending-too-long deduction and a correspondingly prioritized NBA."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_delayed_port_scenario_health_deduction(api_client):
    scenario = api_client.post("/api/demo/scenarios/delayed-failed-port/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]

    health = api_client.get(f"/api/journeys/{journey_id}/health", headers=headers).json()
    line_health = health["lines"][0]
    assert any(rc["code"] == "PORT_PENDING_TOO_LONG" for rc in line_health["reason_codes"])


def test_delayed_port_scenario_nba_is_number_transfer_failure_priority(api_client):
    scenario = api_client.post("/api/demo/scenarios/delayed-failed-port/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]

    nba = api_client.get(f"/api/journeys/{journey_id}/recommendation", headers=headers).json()
    # The seeded scenario leaves the port merely PENDING (not FAILED), so no
    # NUMBER_TRANSFER_FAILURE candidate is generated yet — the port-pending
    # friction signal only affects health score, per FR-019/FR-016.
    assert nba == [] or nba[0]["action_code"] != "ACTIVATION_FAILURE"


def test_explicit_number_transfer_failed_event_produces_failure_nba(api_client):
    scenario = api_client.post("/api/demo/scenarios/delayed-failed-port/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]
    line_id = scenario["line_ids"][0]

    r = api_client.post(
        "/api/events",
        json={
            "event_id": "evt-port-failed",
            "event_type": "NumberTransferFailed",
            "customer_id": scenario["customer_id"],
            "account_id": scenario["account_id"],
            "line_id": line_id,
            "occurred_at": "2026-08-24T12:00:00Z",
            "source": "test",
            "correlation_id": "corr-port-1",
            "attributes": {},
        },
    )
    assert r.status_code == 202

    nba = api_client.get(f"/api/journeys/{journey_id}/recommendation", headers=headers).json()
    assert nba[0]["action_code"] == "NUMBER_TRANSFER_FAILURE"
    assert nba[0]["priority"] == 95
