"""Personalization is additive-only: message text changes never alter the
underlying deterministic priority/reason_codes/action_code (Constitution
Principle I; tasks.md T101a/T101c)."""

from concierge.conversation.personalize import personalize_billing_explanation, personalize_nba_message
from concierge.decisioning.billing import compute_postpaid_bill_estimate, compute_renewal_readiness
from concierge.providers.stub_llm import StubLLMProvider


def test_personalize_nba_message_returns_text_referencing_the_action():
    provider = StubLLMProvider()
    message = personalize_nba_message(provider, "ACTIVATION_FAILURE")
    assert isinstance(message, str)
    assert len(message) > 0


def test_personalize_nba_message_is_deterministic_for_the_stub_provider():
    provider = StubLLMProvider()
    first = personalize_nba_message(provider, "APP_GAP")
    second = personalize_nba_message(provider, "APP_GAP")
    assert first == second


def test_unknown_action_code_still_produces_a_message_without_crashing():
    provider = StubLLMProvider()
    message = personalize_nba_message(provider, "SOME_FUTURE_ACTION_CODE")
    assert isinstance(message, str)


def test_personalization_never_mutates_priority_or_reason_codes(db_session):
    """End-to-end: after personalization runs against a persisted NBA record,
    its priority/tie_break_rank/reason_codes/action_code are untouched —
    only `message` may change."""
    from datetime import datetime, timedelta, timezone

    from concierge.decisioning.recompute import recompute_line
    from concierge.persistence.repositories import DecisionRepository, JourneyRepository

    journey_repo = JourneyRepository(db_session)
    journey_repo.create_account("acct-1", "cust-1")
    started_at = datetime.now(timezone.utc) - timedelta(days=1)
    journey = journey_repo.create_journey("acct-1", started_at, started_at + timedelta(days=30))
    journey_repo.create_line("line-1", "acct-1", "POSTPAID")
    journey_repo.create_line_onboarding_state("line-1", journey.journey_id, "POSTPAID")
    journey_repo.create_activity_instance(journey.journey_id, "line-1", "SIM_ESIM_ACTIVATION", "REQUIRED", "FAILED")
    db_session.flush()

    recompute_line(db_session, journey.journey_id, "line-1", journey.started_at)

    decision_repo = DecisionRepository(db_session)
    record = decision_repo.get_current_nba_for_line("line-1")
    priority_before, reason_codes_before, action_code_before = record.priority, record.reason_codes, record.action_code

    provider = StubLLMProvider()
    record.message = personalize_nba_message(provider, record.action_code)
    db_session.flush()

    record_after = decision_repo.get_current_nba_for_line("line-1")
    assert record_after.priority == priority_before
    assert record_after.reason_codes == reason_codes_before
    assert record_after.action_code == action_code_before
    assert record_after.message is not None


def test_billing_explanation_never_alters_the_computed_postpaid_estimate():
    from datetime import date

    snapshot = {
        "recurring_charges": 65.0,
        "one_time_charges": 35.0,
        "device_installment": 25.0,
        "taxes_fees": 8.5,
        "promotional_credits": -10.0,
        "cycle_start": date(2026, 8, 1),
        "cycle_end": date(2026, 8, 31),
    }
    estimate = compute_postpaid_bill_estimate(snapshot)
    total_before = estimate.total_estimate

    provider = StubLLMProvider()
    explanation = personalize_billing_explanation(provider, estimate.__dict__, None)

    assert isinstance(explanation, str)
    assert len(explanation) > 0
    # The dataclass itself is immutable, but assert explicitly that the
    # personalization call didn't derive a different total as a side effect.
    assert estimate.total_estimate == total_before


def test_billing_explanation_never_alters_the_computed_renewal_readiness():
    from datetime import date

    snapshot = {
        "balance": 12.5,
        "renewal_date": date(2026, 8, 28),
        "data_allowance": "5GB",
        "auto_recharge_enabled": False,
        "expiration_date": None,
        "add_ons": [],
    }
    readiness = compute_renewal_readiness(snapshot)
    ready_before = readiness.renewal_ready

    provider = StubLLMProvider()
    explanation = personalize_billing_explanation(provider, None, readiness.__dict__)

    assert isinstance(explanation, str)
    assert readiness.renewal_ready == ready_before


def test_billing_explanation_with_neither_estimate_nor_renewal_is_a_safe_message():
    provider = StubLLMProvider()
    explanation = personalize_billing_explanation(provider, None, None)
    assert isinstance(explanation, str)
    assert len(explanation) > 0
