"""E2E: multi-line postpaid account. Each line ranks its own NBA
independently (Clarifications Q2), and the account journey/health reflect
per-line progress correctly."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_multiline_journey_full_walkthrough(api_client):
    scenario = api_client.post("/api/demo/scenarios/multi-line-postpaid/reset").json()
    journey_id = scenario["journey_id"]
    headers = _login(api_client, scenario["customer_id"])
    assert len(scenario["line_ids"]) == 2
    line_1, line_2 = scenario["line_ids"]

    # Seed already completes line 1's activation; line 2 has none started.
    journey = api_client.get(f"/api/journeys/{journey_id}", headers=headers).json()
    line_states = {ln["line_id"]: ln for ln in journey["lines"]}
    line_1_sim = next(a for a in line_states[line_1]["activities"] if a["activity_code"] == "SIM_ESIM_ACTIVATION")
    line_2_sim = next(a for a in line_states[line_2]["activities"] if a["activity_code"] == "SIM_ESIM_ACTIVATION")
    assert line_1_sim["status"] == "COMPLETED"
    assert line_2_sim["status"] == "NOT_STARTED"

    # Account-level health is the minimum of the two lines (line 2 is worse off).
    health = api_client.get(f"/api/journeys/{journey_id}/health", headers=headers).json()
    scores_by_line = {h["line_id"]: h["score"] for h in health["lines"]}
    assert health["account"]["score"] == min(scores_by_line.values())

    # Fail line 2's activation — line 1's NBA must stay unaffected (independent ranking).
    r = api_client.post(
        "/api/events",
        json={
            "event_id": "e2e-evt-line2-fail",
            "event_type": "DeviceActivationStarted",
            "customer_id": scenario["customer_id"],
            "account_id": scenario["account_id"],
            "line_id": line_2,
            "occurred_at": "2026-08-24T12:00:00Z",
            "source": "test",
            "correlation_id": "e2e-corr-line2-a",
            "attributes": {},
        },
    )
    assert r.status_code == 202
    r2 = api_client.post(
        "/api/events",
        json={
            "event_id": "e2e-evt-line2-fail-2",
            "event_type": "DeviceActivationFailed",
            "customer_id": scenario["customer_id"],
            "account_id": scenario["account_id"],
            "line_id": line_2,
            "occurred_at": "2026-08-24T12:01:00Z",
            "source": "test",
            "correlation_id": "e2e-corr-line2-b",
            "attributes": {},
        },
    )
    assert r2.status_code == 202

    nba = api_client.get(f"/api/journeys/{journey_id}/recommendation", headers=headers).json()
    nba_by_line = {n["line_id"]: n for n in nba}
    assert nba_by_line[line_2]["action_code"] == "ACTIVATION_FAILURE"
    # Line 1 already completed activation, so it should not also show ACTIVATION_FAILURE.
    if line_1 in nba_by_line:
        assert nba_by_line[line_1]["action_code"] != "ACTIVATION_FAILURE"

    # Account journey is not COMPLETE while line 2 has a required activity failed.
    journey_after = api_client.get(f"/api/journeys/{journey_id}", headers=headers).json()
    assert journey_after["status"] != "COMPLETE"
