"""E2E: prepaid renewal approaching. Verifies the prepaid line's adoption
gap (auto-recharge) surfaces correctly at day 23, and that chat still works
for prepaid customers end to end.

NOTE: contracts/openapi.yaml's GET /journeys/{id}/billing (FR-026 renewal
readiness) was documented but never implemented in this MVP slice (Phase 6
billing/renewal, T075-T082, is out of scope for this build) — so this test
verifies journey/health/NBA/chat behavior for a prepaid line, not the
billing-specific "explain my renewal" grounding the original task envisioned.
"""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def test_prepaid_renewal_scenario_full_walkthrough(api_client):
    scenario = api_client.post("/api/demo/scenarios/prepaid-renewal-approaching/reset").json()
    journey_id = scenario["journey_id"]
    headers = _login(api_client, scenario["customer_id"])

    journey = api_client.get(f"/api/journeys/{journey_id}", headers=headers).json()
    assert journey["current_day"] >= 23
    assert journey["lines"][0]["plan_type"] == "PREPAID"

    # Past the auto-recharge gap threshold (day 7), with security already
    # handled by the seed's CustomerLoggedIn event — the auto-recharge gap
    # should be the surfaced NBA.
    nba = api_client.get(f"/api/journeys/{journey_id}/recommendation", headers=headers).json()
    assert nba[0]["action_code"] == "AUTOPAY_AUTO_RECHARGE_GAP"

    health = api_client.get(f"/api/journeys/{journey_id}/health", headers=headers).json()
    assert any(rc["code"] == "AUTOPAY_AUTO_RECHARGE_INCOMPLETE" for rc in health["lines"][0]["reason_codes"])

    # Chat still works for a prepaid customer, grounded in real knowledge.
    chat = api_client.post(
        "/api/chat", json={"session_id": "e2e-2", "message": "how do I turn on auto-recharge?"}, headers=headers
    ).json()
    assert chat["authenticated"] is True
    assert any(s["topic"] == "auto-recharge" for s in chat["sources"])

    # Enabling it resolves the gap.
    r = api_client.post(
        "/api/events",
        json={
            "event_id": "e2e-evt-autorecharge",
            "event_type": "AutoRechargeEnabled",
            "customer_id": scenario["customer_id"],
            "account_id": scenario["account_id"],
            "line_id": scenario["line_ids"][0],
            "occurred_at": "2026-08-24T12:00:00Z",
            "source": "test",
            "correlation_id": "e2e-corr-autorecharge",
            "attributes": {},
        },
    )
    assert r.status_code == 202

    nba_after = api_client.get(f"/api/journeys/{journey_id}/recommendation", headers=headers).json()
    assert not any(a["action_code"] == "AUTOPAY_AUTO_RECHARGE_GAP" for a in nba_after)
