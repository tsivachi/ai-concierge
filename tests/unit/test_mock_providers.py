from concierge.providers.mock_notification import MockNotificationProvider
from concierge.providers.mock_order import MockOrderProvider
from concierge.providers.mock_risk_scoring import MockRiskScoringProvider
from concierge.providers.mock_support import MockSupportProvider


def test_mock_customer_provider_reads_seeded_account(db_session):
    from concierge.persistence.repositories import JourneyRepository
    from concierge.providers.mock_customer import MockCustomerProvider

    JourneyRepository(db_session).create_account("acct-1", "cust-1")
    provider = MockCustomerProvider(db_session)

    assert provider.get_customer("cust-1") == {"customer_id": "cust-1", "account_id": "acct-1"}
    assert provider.get_customer("unknown") is None


def test_mock_order_provider_is_deterministic_for_same_id():
    provider = MockOrderProvider()
    first = provider.get_order("order-123")
    second = provider.get_order("order-123")
    assert first == second
    assert first["status"] == "COMPLETED"


def test_mock_order_provider_differs_by_id():
    provider = MockOrderProvider()
    assert provider.get_order("order-1") != provider.get_order("order-2")


def test_mock_notification_provider_returns_deterministic_receipt():
    provider = MockNotificationProvider()
    first = provider.send("cust-1", "push", "hello")
    second = provider.send("cust-1", "push", "hello")
    assert first == second
    assert first["status"] == "sent"


def test_mock_notification_provider_rejects_unsupported_channel():
    provider = MockNotificationProvider()
    import pytest

    with pytest.raises(ValueError):
        provider.send("cust-1", "carrier_pigeon", "hi")


def test_mock_support_provider_is_deterministic_for_same_case_id():
    provider = MockSupportProvider()
    payload = {"case_id": "case-1", "reason": "BILLING_DISPUTE"}
    assert provider.create_case(payload) == provider.create_case(payload)


def test_mock_risk_scoring_provider_is_deterministic_and_bounded():
    provider = MockRiskScoringProvider()
    first = provider.score("acct-1", "line-1")
    second = provider.score("acct-1", "line-1")
    assert first == second
    for value in first.values():
        assert 0.0 <= value <= 1.0


def test_mock_risk_scoring_provider_differs_across_accounts():
    provider = MockRiskScoringProvider()
    assert provider.score("acct-1", None) != provider.score("acct-2", None)
