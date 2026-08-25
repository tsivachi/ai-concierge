"""E2E: human escalation with context. The unresolved activation failure
escalates automatically on first chat contact, with a case containing
everything a human agent needs — no repeated explanation required."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_human_escalation_full_walkthrough(api_client):
    scenario = api_client.post("/api/demo/scenarios/human-escalation-with-context/reset").json()
    journey_id = scenario["journey_id"]
    headers = _login(api_client, scenario["customer_id"])

    chat = api_client.post(
        "/api/chat",
        json={"session_id": "e2e-esc-1", "message": "I really need help, nothing is working"},
        headers=headers,
    ).json()
    assert chat["escalated"] is True
    case_id = chat["escalation_case_id"]

    case = api_client.get(f"/api/escalations?case_id={case_id}", headers=headers).json()
    assert case["status"] == "OPEN"
    assert case["reason"] == "UNRESOLVED_ACTIVATION_OR_PORT"
    assert case["journey_id"] == journey_id
    assert case["journey_snapshot"]["activities"]
    assert case["relevant_event_ids"]
    assert case["conversation_summary"]

    # Explicit "talk to a human" also escalates (a different trigger, same
    # journey) — but since an open case already exists for the related
    # action, it reuses it rather than duplicating.
    chat2 = api_client.post(
        "/api/chat", json={"session_id": "e2e-esc-1", "message": "can I talk to a human?"}, headers=headers
    ).json()
    assert chat2["escalated"] is True
    assert chat2["escalation_case_id"] == case_id

    # A reviewer can also trigger escalation directly (e.g. a "talk to a
    # human" UI button) via POST /api/escalations, independent of chat.
    explicit = api_client.post(
        "/api/escalations",
        json={"journey_id": journey_id, "line_id": scenario["line_ids"][0], "reason": "EXPLICIT_REQUEST"},
        headers=headers,
    )
    assert explicit.status_code == 201
    assert explicit.json()["reason"] == "EXPLICIT_REQUEST"
    # (Cross-account access rejection is covered by test_auth_boundary.py;
    # scenario reset here would wipe this case, so it isn't re-tested here.)
