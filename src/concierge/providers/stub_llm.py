"""Default LLMProvider (FR-013, FR-025, FR-026): deterministic, template-based
responses that reference only fields present in the supplied context — no
network calls, no API key required. Makes the whole app runnable without any
external LLM (research.md §4)."""


class StubLLMProvider:
    def generate(self, prompt: str, context: dict) -> str:
        kind = context.get("kind", "generic")

        if kind == "nba_message":
            return self._nba_message(context)
        if kind == "billing_explanation":
            return self._billing_explanation(context)
        if kind == "chat_answer":
            return self._chat_answer(context)
        if kind == "unsupported_action":
            return self._unsupported_action(context)

        return "I don't have enough information to answer that yet."

    def _nba_message(self, context: dict) -> str:
        label = context.get("label", "your next step")
        return f"Your next step is: {label}. Take care of this to keep your onboarding on track."

    def _billing_explanation(self, context: dict) -> str:
        estimate = context.get("estimate")
        if estimate is None:
            return "Your renewal is ready to review whenever you'd like."
        return (
            f"Here's your billing/renewal summary: {estimate}, based on the figures already on file "
            "for your account. This is an estimate, not a final bill or renewal confirmation."
        )

    def _chat_answer(self, context: dict) -> str:
        sources = context.get("sources", [])
        nba_label = context.get("current_nba_label")
        parts = []
        if nba_label:
            parts.append(f"Your current recommended next step is: {nba_label}.")
        if sources:
            titles = ", ".join(s["title"] for s in sources)
            parts.append(f"Based on our guides on {titles}, here's what typically helps.")
        if not parts:
            parts.append("I don't have a specific answer for that yet — let me connect you with a human agent.")
        return " ".join(parts)

    def _unsupported_action(self, context: dict) -> str:
        return (
            "I'm not able to do that directly, but I can walk you through the supported steps, "
            "or connect you with a human agent if you'd like."
        )
