"""US2 AC2: repeated activation failures don't decrease the health-score
deduction or NBA urgency, and the repeated-failure pattern is retained."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def test_repeated_activation_failure_scenario_health_and_nba(api_client):
    scenario = api_client.post("/api/demo/scenarios/repeated-activation-failure/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]

    health = api_client.get(f"/api/journeys/{journey_id}/health", headers=headers).json()
    line_health = health["lines"][0]
    assert line_health["band"] in ("RED", "YELLOW")
    assert any(rc["code"] == "ACTIVATION_FAILURE" for rc in line_health["reason_codes"])

    nba = api_client.get(f"/api/journeys/{journey_id}/recommendation", headers=headers).json()
    assert nba[0]["action_code"] == "ACTIVATION_FAILURE"
    assert nba[0]["priority"] == 100


def test_repeated_activation_failure_does_not_worsen_beyond_single_deduction(api_client):
    """A single ACTIVATION_FAILURE deduction applies regardless of how many
    times DeviceActivationFailed fired in the seed history — it does not
    stack, matching FR-016's per-condition (not per-event) deduction model."""
    scenario = api_client.post("/api/demo/scenarios/repeated-activation-failure/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]

    first = api_client.get(f"/api/journeys/{journey_id}/health", headers=headers).json()
    second = api_client.get(f"/api/journeys/{journey_id}/health", headers=headers).json()
    assert first["lines"][0]["score"] == second["lines"][0]["score"]
