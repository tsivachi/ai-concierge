"""GET /api/dashboard reflects counts after running several scenarios, and
the simulated POCR/PORR figures are always visibly labeled (FR-035, SC-009)."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_dashboard_is_unauthenticated(api_client):
    r = api_client.get("/api/dashboard")
    assert r.status_code == 200


def test_dashboard_pocr_porr_always_labeled_simulated(api_client):
    body = api_client.get("/api/dashboard").json()
    assert body["simulated"] is True
    assert body["label"]


def test_dashboard_reflects_enrolled_customers_after_loading_scenarios(api_client):
    api_client.post("/api/demo/scenarios/postpaid-device-port-in/reset")
    body = api_client.get("/api/dashboard").json()
    assert body["enrolled_customers"] >= 1


def test_dashboard_reflects_escalations_after_one_occurs(api_client):
    scenario = api_client.post("/api/demo/scenarios/human-escalation-with-context/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    api_client.post("/api/chat", json={"session_id": "dash-1", "message": "my activation is broken"}, headers=headers)

    body = api_client.get("/api/dashboard").json()
    assert body["escalations"] >= 1


def test_dashboard_response_shape_matches_contract(api_client):
    body = api_client.get("/api/dashboard").json()
    assert set(body.keys()) == {
        "simulated",
        "enrolled_customers",
        "engagement",
        "onboarding_completion_rate",
        "digital_resolutions",
        "escalations",
        "potential_pocr_interventions",
        "potential_porr_interventions",
        "label",
    }
    assert set(body["engagement"].keys()) == {"proactive_contacts_delivered", "chat_sessions"}
