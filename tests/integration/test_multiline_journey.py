"""US1 AC4: on a multi-line account, one line completing while another lags
keeps the account journey overall incomplete, while each line's own status
accurately reflects its individual progress."""


def _login(client, customer_id):
    r = client.post("/api/auth/login", json={"customer_id": customer_id})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _post_event(client, event_id, event_type, scenario, line_id, occurred_at):
    return client.post(
        "/api/events",
        json={
            "event_id": event_id,
            "event_type": event_type,
            "customer_id": scenario["customer_id"],
            "account_id": scenario["account_id"],
            "line_id": line_id,
            "occurred_at": occurred_at,
            "source": "test",
            "correlation_id": event_id,
            "attributes": {},
        },
    )


def test_one_line_complete_other_incomplete_keeps_account_incomplete(api_client):
    scenario = api_client.post("/api/demo/scenarios/multi-line-postpaid/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]
    line_1, line_2 = scenario["line_ids"]

    # Complete line 1 fully (activation already done by the seed; finish port + security).
    _post_event(api_client, "ml-1", "NumberTransferRequested", scenario, line_1, "2026-08-24T00:00:00Z")
    _post_event(api_client, "ml-2", "NumberTransferCompleted", scenario, line_1, "2026-08-24T00:05:00Z")
    _post_event(api_client, "ml-3", "CustomerLoggedIn", scenario, line_1, "2026-08-24T00:06:00Z")

    # Line 2 gets no events at all — still fully open.
    journey = api_client.get(f"/api/journeys/{journey_id}", headers=headers).json()
    lines_by_id = {ln["line_id"]: ln for ln in journey["lines"]}

    assert lines_by_id[line_1]["status"] == "COMPLETE"
    assert lines_by_id[line_2]["status"] == "IN_PROGRESS"
    assert journey["status"] != "COMPLETE"


def test_completing_both_lines_completes_the_account(api_client):
    scenario = api_client.post("/api/demo/scenarios/multi-line-postpaid/reset").json()
    headers = _login(api_client, scenario["customer_id"])
    journey_id = scenario["journey_id"]
    line_1, line_2 = scenario["line_ids"]

    for i, line_id in enumerate((line_1, line_2)):
        _post_event(api_client, f"ml2-{i}-a", "DeviceActivationStarted", scenario, line_id, "2026-08-24T00:00:00Z")
        _post_event(api_client, f"ml2-{i}-b", "DeviceActivationCompleted", scenario, line_id, "2026-08-24T00:01:00Z")
        _post_event(api_client, f"ml2-{i}-c", "NumberTransferRequested", scenario, line_id, "2026-08-24T00:02:00Z")
        _post_event(api_client, f"ml2-{i}-d", "NumberTransferCompleted", scenario, line_id, "2026-08-24T00:03:00Z")

    # ACCOUNT_SECURITY is shared once per journey.
    _post_event(api_client, "ml2-security", "CustomerLoggedIn", scenario, line_1, "2026-08-24T00:04:00Z")

    journey = api_client.get(f"/api/journeys/{journey_id}", headers=headers).json()
    assert all(ln["status"] == "COMPLETE" for ln in journey["lines"])
    assert journey["status"] == "COMPLETE"
