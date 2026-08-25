"""E2E: postpaid activation failure — reset scenario, observe health/NBA
reflect the failure, chat about it, and confirm it escalates with full
context. Exercises US1 (enrollment/state), US2 (friction/NBA/escalation),
and US4 (chat) together, end to end through the real HTTP API."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_postpaid_activation_failure_full_walkthrough(api_client):
    # 1. Load the scenario.
    scenario = api_client.post("/api/demo/scenarios/repeated-activation-failure/reset").json()
    journey_id = scenario["journey_id"]
    line_id = scenario["line_ids"][0]
    headers = _login(api_client, scenario["customer_id"])

    # 2. Confirm the journey view shows the failed activation.
    journey = api_client.get(f"/api/journeys/{journey_id}", headers=headers).json()
    sim_activity = next(a for a in journey["lines"][0]["activities"] if a["activity_code"] == "SIM_ESIM_ACTIVATION")
    assert sim_activity["status"] == "FAILED"

    # 3. Health score reflects the failure with reason codes.
    health = api_client.get(f"/api/journeys/{journey_id}/health", headers=headers).json()
    assert health["lines"][0]["band"] in ("RED", "YELLOW")
    assert any(rc["code"] == "ACTIVATION_FAILURE" for rc in health["lines"][0]["reason_codes"])

    # 4. NBA is the highest-priority action.
    nba = api_client.get(f"/api/journeys/{journey_id}/recommendation", headers=headers).json()
    assert nba[0]["action_code"] == "ACTIVATION_FAILURE"
    assert nba[0]["priority"] == 100
    assert nba[0]["message"]  # LLM-personalized wording present

    # 5. Chatting about it escalates automatically with full context.
    chat = api_client.post(
        "/api/chat", json={"session_id": "e2e-1", "message": "why does my phone still not work?"}, headers=headers
    ).json()
    assert chat["escalated"] is True

    case = api_client.get(f"/api/escalations?case_id={chat['escalation_case_id']}", headers=headers).json()
    assert case["reason"] == "UNRESOLVED_ACTIVATION_OR_PORT"
    assert case["line_id"] == line_id
    assert case["journey_snapshot"]["activities"]
    assert case["relevant_event_ids"]

    # 6. That issue no longer surfaces as a fresh NBA (suppressed while open).
    nba_after = api_client.get(f"/api/journeys/{journey_id}/recommendation", headers=headers).json()
    assert not any(a["action_code"] == "ACTIVATION_FAILURE" for a in nba_after)

    # 7. Dashboard reflects the escalation.
    dashboard = api_client.get("/api/dashboard").json()
    assert dashboard["escalations"] >= 1
    assert dashboard["simulated"] is True
