from dataclasses import dataclass

from concierge.domain.enums import ActivityScope, PlanType, RequirementClass


@dataclass(frozen=True)
class ReasonCode:
    """A machine-readable factor behind a health score or NBA decision (FR-018).

    `code` is a short, stable identifier derived 1:1 from the already-named
    deduction/priority factors in FR-016/FR-011 (spec.md Assumptions).
    """

    code: str
    label: str
    deduction: int | None = None


@dataclass(frozen=True)
class ActivityDefinition:
    """One row of the static REQUIRED/RECOMMENDED/OPTIONAL activity catalog
    (data-model.md §ActivityDefinition), keyed by (plan_type, activity_code)."""

    activity_code: str
    scope: ActivityScope
    plan_type: PlanType
    requirement_class: RequirementClass
