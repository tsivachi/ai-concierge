"""Provider Protocols (FR-029): every external dependency is accessed through
one of these interfaces. Real implementations, when they exist, satisfy the
same Protocol — callers never change (Constitution Principle II)."""

from typing import Protocol


class CustomerProvider(Protocol):
    def get_customer(self, customer_id: str) -> dict | None: ...


class OrderProvider(Protocol):
    def get_order(self, order_id: str) -> dict | None: ...


class BillingProvider(Protocol):
    def get_billing_snapshot(self, line_id: str) -> dict | None: ...
    def get_renewal_snapshot(self, line_id: str) -> dict | None: ...


class NotificationProvider(Protocol):
    """FR-030: must support multiple channels conceptually — push, SMS,
    email, in-app — without a real integration to any of them."""

    def send(self, customer_id: str, channel: str, message: str) -> dict: ...


class SupportProvider(Protocol):
    def create_case(self, escalation_payload: dict) -> dict: ...


class RiskScoringProvider(Protocol):
    def score(self, account_id: str | None, line_id: str | None) -> dict: ...


class LLMProvider(Protocol):
    def generate(self, prompt: str, context: dict) -> str: ...


class EmbeddingProvider(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


__all__ = [
    "CustomerProvider",
    "OrderProvider",
    "BillingProvider",
    "NotificationProvider",
    "SupportProvider",
    "RiskScoringProvider",
    "LLMProvider",
    "EmbeddingProvider",
]
