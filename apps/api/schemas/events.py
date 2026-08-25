from datetime import datetime

from pydantic import BaseModel

from concierge.domain.enums import EventType


class EventIn(BaseModel):
    """Mirrors contracts/openapi.yaml's DomainEvent schema (FR-006, FR-007)."""

    event_id: str
    event_type: EventType
    customer_id: str
    account_id: str
    line_id: str | None = None
    journey_id: str | None = None
    occurred_at: datetime
    source: str
    correlation_id: str
    attributes: dict = {}


class EventAck(BaseModel):
    event_id: str
    outcome: str  # applied | duplicate | dead_lettered
