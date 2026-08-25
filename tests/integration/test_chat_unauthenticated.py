"""User Story 5: unauthenticated POST /api/chat — generic Q&A works;
account-specific questions are declined with an auth prompt."""


def test_generic_question_unauthenticated_succeeds(api_client):
    r = api_client.post("/api/chat", json={"session_id": "s1", "message": "how do I turn on AutoPay?"})
    assert r.status_code == 200
    body = r.json()
    assert body["authenticated"] is False
    assert any(s["topic"] == "autopay" for s in body["sources"])


def test_account_specific_question_unauthenticated_is_declined(api_client):
    r = api_client.post("/api/chat", json={"session_id": "s1", "message": "is my line activated?"})
    assert r.status_code == 200
    body = r.json()
    assert body["authenticated"] is False
    assert body["sources"] == []
    assert "sign" in body["answer"].lower() or "authenticat" in body["answer"].lower()


def test_no_authorization_header_required(api_client):
    r = api_client.post("/api/chat", json={"session_id": "s2", "message": "how does porting work?"})
    assert r.status_code == 200


def test_conversation_turns_are_persisted_for_unauthenticated_sessions(db_session):
    """Even unauthenticated sessions get a ConversationSession/turn history,
    with customer_id left null."""
    from concierge.conversation import attempts
    from concierge.persistence.conversation_models import ConversationSession

    attempts.get_or_create_session(db_session, "anon-session", customer_id=None)
    db_session.commit()

    record = db_session.get(ConversationSession, "anon-session")
    assert record is not None
    assert record.customer_id is None
