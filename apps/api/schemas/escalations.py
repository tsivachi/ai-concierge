from datetime import datetime

from pydantic import BaseModel

REASON_VALUES = (
    "EXPLICIT_REQUEST",
    "UNSUPPORTED_LOW_CONFIDENCE",
    "TWO_FAILED_TROUBLESHOOTING",
    "UNRESOLVED_ACTIVATION_OR_PORT",
    "BILLING_DISPUTE",
    "SENSITIVE_ACCOUNT_SECURITY",
)


class EscalationCreateIn(BaseModel):
    journey_id: str
    line_id: str | None = None
    reason: str
    session_id: str | None = None


class EscalationCaseOut(BaseModel):
    case_id: str
    journey_id: str
    line_id: str | None
    reason: str
    priority: int
    journey_snapshot: dict
    relevant_event_ids: list[str]
    attempted_action_ids: list[str]
    conversation_summary: str | None
    status: str
    created_at: datetime
