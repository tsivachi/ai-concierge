import pytest

from concierge.knowledge.ingest import ingest_knowledge_base
from concierge.knowledge.retrieval import search_knowledge

CANNED_QUERIES = [
    ("my new line still hasn't activated after 15 minutes, what should I do", "activation"),
    ("what's the difference between eSIM and a physical SIM", "esim-sim"),
    ("how long does porting my number take", "porting"),
    ("how do I set up voicemail", "voicemail"),
    ("how do I download and sign into the mobile app", "app"),
    ("how do I secure my account with a PIN", "security"),
    ("what are the charges on my postpaid bill", "billing"),
    ("why is my first bill higher than expected", "first-bill"),
    ("how do I turn on AutoPay", "autopay"),
    ("how do I set up auto-recharge for my prepaid plan", "auto-recharge"),
    ("should I add device protection coverage", "device-protection"),
    ("my phone has no signal, how do I troubleshoot", "network-troubleshooting"),
    ("how much data have I used on my plan", "plan-data-usage"),
    ("how do I use my phone while traveling internationally", "international-usage"),
    ("when does my prepaid plan renew", "prepaid-renewal"),
]


@pytest.fixture(autouse=True)
def _ingested(db_session, tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "chroma"))
    import concierge.knowledge.ingest as ingest_module

    ingest_module.reset_chroma_client_for_tests()
    ingest_knowledge_base(db_session)
    db_session.commit()
    yield
    ingest_module.reset_chroma_client_for_tests()


@pytest.mark.parametrize("query,expected_topic", CANNED_QUERIES)
def test_top_result_matches_expected_topic(query, expected_topic):
    results = search_knowledge(query, top_k=1)
    assert results
    assert results[0].topic == expected_topic


def test_search_returns_source_metadata():
    results = search_knowledge("how do I activate my line", top_k=1)
    assert results[0].doc_id
    assert results[0].title
    assert results[0].topic
    assert 0.0 <= results[0].score <= 1.0


def test_empty_collection_returns_no_results(tmp_path, monkeypatch):
    monkeypatch.setenv("CHROMA_PERSIST_DIR", str(tmp_path / "empty_chroma"))
    import concierge.knowledge.ingest as ingest_module

    ingest_module.reset_chroma_client_for_tests()
    try:
        assert search_knowledge("anything") == []
    finally:
        ingest_module.reset_chroma_client_for_tests()
