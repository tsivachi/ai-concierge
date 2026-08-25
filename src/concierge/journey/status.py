"""Line- and account-level onboarding-completion derivation (FR-005), and the
journey EXPIRED transition. Pure functions over already-loaded state — no I/O
here, so the router stays a thin composition layer (Constitution Principle IX)."""

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass(frozen=True)
class ActivityStatusView:
    activity_code: str
    status: str
    requirement_class: str


def is_line_complete(line_activities: list[ActivityStatusView], account_activities: list[ActivityStatusView]) -> bool:
    """A line is COMPLETE when every REQUIRED activity applicable to it
    (its own line-scoped activities, plus the journey's account-scoped ones)
    is COMPLETED or NOT_APPLICABLE (FR-005)."""
    required = [a for a in line_activities + account_activities if a.requirement_class == "REQUIRED"]
    return all(a.status in ("COMPLETED", "NOT_APPLICABLE") for a in required)


def derive_journey_status(
    line_complete_flags: list[bool], expires_at: datetime, as_of: datetime | None = None
) -> str:
    """ACTIVE -> COMPLETE when every line is complete; ACTIVE -> EXPIRED when
    now() > expires_at and not yet complete (spec.md Assumptions)."""
    as_of = as_of or datetime.now(timezone.utc)
    expires_at = expires_at if expires_at.tzinfo else expires_at.replace(tzinfo=timezone.utc)

    if line_complete_flags and all(line_complete_flags):
        return "COMPLETE"
    if as_of > expires_at:
        return "EXPIRED"
    return "ACTIVE"
