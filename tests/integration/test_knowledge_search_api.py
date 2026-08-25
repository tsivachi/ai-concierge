"""GET /api/knowledge/search is unauthenticated and returns grounded,
non-account-specific results (FR-020)."""


def test_search_requires_no_authentication(api_client):
    r = api_client.get("/api/knowledge/search", params={"q": "how do I set up voicemail"})
    assert r.status_code == 200
    results = r.json()
    assert results
    assert results[0]["topic"] == "voicemail"


def test_search_results_contain_no_account_specific_fields(api_client):
    r = api_client.get("/api/knowledge/search", params={"q": "how do I turn on AutoPay"})
    results = r.json()
    for result in results:
        assert set(result.keys()) == {"doc_id", "title", "topic", "snippet", "score"}


def test_search_requires_a_query_param(api_client):
    r = api_client.get("/api/knowledge/search")
    assert r.status_code == 422
