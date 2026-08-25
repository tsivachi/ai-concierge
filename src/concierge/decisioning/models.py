"""Pure value objects shared by the decisioning modules. No I/O, no LLM
calls anywhere in this package (Constitution Principle I)."""

from dataclasses import dataclass, field

from concierge.domain.enums import ActivityStatus, RequirementClass


@dataclass(frozen=True)
class ActivitySnapshot:
    activity_code: str
    requirement_class: RequirementClass
    status: ActivityStatus


@dataclass(frozen=True)
class FrictionFlags:
    """Detection signals from decisioning/friction.py (FR-019)."""

    port_pending_too_long: bool = False
    repeated_help_visit: bool = False
    unresolved_repeated_chat: bool = False
    setup_abandoned_activity_codes: frozenset[str] = field(default_factory=frozenset)


@dataclass(frozen=True)
class HealthScoreResult:
    score: int
    band: str
    reason_codes: list[dict]  # [{code, label, deduction}]


@dataclass(frozen=True)
class NBACandidate:
    line_id: str
    action_code: str
    priority: int
    tie_break_rank: int
    reason_codes: list[dict]


@dataclass(frozen=True)
class OutreachDecision:
    candidate: NBACandidate
    status: str  # DELIVERED | SUPPRESSED
    suppression_reason: str | None = None
