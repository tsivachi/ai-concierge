"""FR-020/FR-021: the unauthenticated engine path never receives or returns
customer-specific fields — it takes only a question string and never touches
persistence or ConciergeContext."""

import inspect

from concierge.conversation.engine import answer_unauthenticated, looks_account_specific
from concierge.providers.stub_llm import StubLLMProvider


def test_answer_unauthenticated_signature_has_no_customer_or_session_parameter():
    sig = inspect.signature(answer_unauthenticated)
    param_names = set(sig.parameters.keys())
    assert param_names == {"question", "llm_provider"}


def test_generic_question_returns_grounded_answer_with_sources():
    provider = StubLLMProvider()
    result = answer_unauthenticated("how do I set up voicemail?", provider)
    assert result.authenticated is False
    assert result.declined is False
    assert result.sources


def test_account_specific_question_is_declined_not_answered():
    provider = StubLLMProvider()
    result = answer_unauthenticated("is my line activated yet?", provider)
    assert result.declined is True
    assert result.sources == []
    assert "sign" in result.answer.lower() or "authenticat" in result.answer.lower()


def test_declined_answer_contains_no_customer_identifiers():
    provider = StubLLMProvider()
    result = answer_unauthenticated("what is my account balance?", provider)
    for forbidden in ("cust-", "acct-", "line-"):
        assert forbidden not in result.answer


def test_looks_account_specific_matches_common_phrasings():
    assert looks_account_specific("is my line activated?") is True
    assert looks_account_specific("what's my balance?") is True
    assert looks_account_specific("how does eSIM setup work?") is False
