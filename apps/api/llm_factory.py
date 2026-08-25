"""LLMProvider selection (research.md §4): AnthropicLLMProvider only when
ANTHROPIC_API_KEY is set, StubLLMProvider otherwise — the app is always
fully functional without an API key."""

import os

from concierge.providers.stub_llm import StubLLMProvider

_provider = None


def get_llm_provider():
    global _provider
    if _provider is not None:
        return _provider

    if os.environ.get("ANTHROPIC_API_KEY"):
        from concierge.providers.anthropic_llm import AnthropicLLMProvider

        _provider = AnthropicLLMProvider()
    else:
        _provider = StubLLMProvider()

    return _provider


def reset_llm_provider_for_tests() -> None:
    global _provider
    _provider = None
