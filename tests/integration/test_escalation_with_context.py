"""US2 AC10 / FR-028: the human-escalation-with-context scenario has an
unresolved activation failure, which must escalate automatically with full
context — the customer should never need to repeat what already happened."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_chat_on_unresolved_activation_failure_escalates_automatically(api_client):
    scenario = api_client.post("/api/demo/scenarios/human-escalation-with-context/reset").json()
    headers = _login(api_client, scenario["customer_id"])

    r = api_client.post(
        "/api/chat", json={"session_id": "esc-sess-1", "message": "why isn't my phone working?"}, headers=headers
    )
    body = r.json()
    assert body["escalated"] is True
    assert body["escalation_case_id"]


def test_escalation_case_has_full_context_without_needing_customer_to_repeat(api_client):
    scenario = api_client.post("/api/demo/scenarios/human-escalation-with-context/reset").json()
    headers = _login(api_client, scenario["customer_id"])

    chat_response = api_client.post(
        "/api/chat", json={"session_id": "esc-sess-2", "message": "my activation is broken"}, headers=headers
    ).json()
    case_id = chat_response["escalation_case_id"]

    case = api_client.get(f"/api/escalations?case_id={case_id}", headers=headers).json()
    assert case["reason"] == "UNRESOLVED_ACTIVATION_OR_PORT"
    assert case["journey_id"] == scenario["journey_id"]
    assert case["line_id"] == scenario["line_ids"][0]
    # Full journey/event context is bundled — no re-explaining required.
    assert case["journey_snapshot"]["activities"]
    assert any(
        a["activity_code"] == "SIM_ESIM_ACTIVATION" and a["status"] == "FAILED"
        for a in case["journey_snapshot"]["activities"]
    )
    assert case["relevant_event_ids"]
    assert case["conversation_summary"]
    assert case["status"] == "OPEN"


def test_repeated_chat_reuses_the_same_open_case_not_a_duplicate(api_client):
    scenario = api_client.post("/api/demo/scenarios/human-escalation-with-context/reset").json()
    headers = _login(api_client, scenario["customer_id"])

    first = api_client.post(
        "/api/chat", json={"session_id": "esc-sess-3", "message": "help, my line still isn't active"}, headers=headers
    ).json()
    second = api_client.post(
        "/api/chat", json={"session_id": "esc-sess-3", "message": "any update on my activation?"}, headers=headers
    ).json()

    assert first["escalation_case_id"] == second["escalation_case_id"]


def test_new_nba_recommendation_no_longer_surfaces_the_escalated_issue(api_client):
    """FR-028a: once escalated, the same issue is suppressed from future
    proactive NBA candidates."""
    scenario = api_client.post("/api/demo/scenarios/human-escalation-with-context/reset").json()
    headers = _login(api_client, scenario["customer_id"])

    api_client.post(
        "/api/chat", json={"session_id": "esc-sess-4", "message": "my activation is stuck"}, headers=headers
    )

    nba = api_client.get(f"/api/journeys/{scenario['journey_id']}/recommendation", headers=headers).json()
    assert not any(a["action_code"] == "ACTIVATION_FAILURE" for a in nba)
