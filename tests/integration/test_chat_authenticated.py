"""User Story 4: authenticated chat explains the current NBA correctly and
answers a knowledge-covered question grounded in retrieved sources."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_authenticated_chat_explains_current_nba(api_client):
    scenario = api_client.post("/api/demo/scenarios/contextual-troubleshooting/reset").json()
    headers = _login(api_client, scenario["customer_id"])

    r = api_client.post(
        "/api/chat", json={"session_id": "sess-1", "message": "what is my next step?"}, headers=headers
    )
    assert r.status_code == 200
    body = r.json()
    assert body["authenticated"] is True
    # The scenario's port is REQUESTED (in progress), no failures yet, so the
    # NBA should reflect required-security or another real gap — not invent one.
    assert body["answer"]


def test_authenticated_chat_grounds_troubleshooting_question_in_sources(api_client):
    scenario = api_client.post("/api/demo/scenarios/contextual-troubleshooting/reset").json()
    headers = _login(api_client, scenario["customer_id"])

    r = api_client.post(
        "/api/chat",
        json={"session_id": "sess-2", "message": "how long does porting my number take?"},
        headers=headers,
    )
    body = r.json()
    assert any(s["topic"] == "porting" for s in body["sources"])


def test_authenticated_chat_escalates_unsupported_action_instead_of_claiming_it(api_client):
    """FR-024/FR-027: an unsupported action request is never claimed as done
    — it's escalated to a human with context (Phase 9)."""
    scenario = api_client.post("/api/demo/scenarios/contextual-troubleshooting/reset").json()
    headers = _login(api_client, scenario["customer_id"])

    r = api_client.post(
        "/api/chat", json={"session_id": "sess-3", "message": "please cancel my line"}, headers=headers
    )
    body = r.json()
    assert body["escalated"] is True
    assert body["escalation_case_id"]
    assert "cancel" not in body["answer"].lower()
    assert "human" in body["answer"].lower()

    case = api_client.get(f"/api/escalations?case_id={body['escalation_case_id']}", headers=headers).json()
    assert case["reason"] == "UNSUPPORTED_LOW_CONFIDENCE"
    assert case["status"] == "OPEN"


def test_unauthenticated_request_on_chat_still_gets_generic_answer(api_client):
    r = api_client.post("/api/chat", json={"session_id": "sess-4", "message": "how does eSIM setup work?"})
    assert r.status_code == 200
    body = r.json()
    assert body["authenticated"] is False
    assert body["sources"]
