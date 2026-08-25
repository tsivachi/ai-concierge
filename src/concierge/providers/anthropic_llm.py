"""Optional real LLMProvider (FR-013), activated only when ANTHROPIC_API_KEY
is set (research.md §4). Same interface as StubLLMProvider — call sites in
conversation/ never know or care which one is wired in. The `anthropic`
package is an optional extra (pyproject.toml `[project.optional-dependencies].llm`);
importing this module never fails even if it isn't installed — only
instantiating AnthropicLLMProvider does, and the factory (apps/api/main.py)
only does that when an API key is present."""

import os

_PROMPT_TEMPLATES = {
    "nba_message": "Personalize this recommended next step in one short, friendly sentence: {label}",
    "billing_explanation": "Explain this billing estimate in plain language, using only these figures: {estimate}",
    "chat_answer": "Answer the customer's question using only this context: {context}",
    "unsupported_action": "Politely explain this request isn't directly supported, offering the alternative: {context}",
}


class AnthropicLLMProvider:
    def __init__(self, model: str = "claude-sonnet-5") -> None:
        try:
            import anthropic
        except ImportError as exc:
            raise RuntimeError(
                "AnthropicLLMProvider requires the 'anthropic' package; install the 'llm' extra "
                "(pip install -e '.[llm]') or unset ANTHROPIC_API_KEY to use StubLLMProvider instead."
            ) from exc

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY is not set")

        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def generate(self, prompt: str, context: dict) -> str:
        kind = context.get("kind", "generic")
        template = _PROMPT_TEMPLATES.get(kind)
        full_prompt = template.format(**{k: context.get(k) for k in ("label", "estimate", "context")}) if template else prompt

        response = self._client.messages.create(
            model=self._model,
            max_tokens=300,
            messages=[{"role": "user", "content": full_prompt}],
        )
        return "".join(block.text for block in response.content if hasattr(block, "text"))
