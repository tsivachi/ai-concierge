"""The postpaid/prepaid REQUIRED/RECOMMENDED/OPTIONAL activity catalog.

Resolves spec.md FR-004/FR-005's reference to "the defined postpaid and
prepaid activity lists" per the table in data-model.md §ActivityDefinition
(itself sourced verbatim from the original feature brief — research.md §10).

`—` in that table (an activity not part of a plan type's catalog at all) is
represented here simply by omitting the entry; that is distinct from
NOT_APPLICABLE, which is a runtime outcome for an *instantiated* activity
(e.g. a port-less number transfer).
"""

from concierge.domain.enums import ActivityScope, PlanType, RequirementClass
from concierge.domain.models import ActivityDefinition

_CATALOG: tuple[ActivityDefinition, ...] = (
    # activity_code, scope, plan_type, requirement_class
    ActivityDefinition("SIM_ESIM_ACTIVATION", ActivityScope.LINE, PlanType.POSTPAID, RequirementClass.REQUIRED),
    ActivityDefinition("SIM_ESIM_ACTIVATION", ActivityScope.LINE, PlanType.PREPAID, RequirementClass.REQUIRED),
    ActivityDefinition("NUMBER_TRANSFER", ActivityScope.LINE, PlanType.POSTPAID, RequirementClass.REQUIRED),
    ActivityDefinition("NUMBER_TRANSFER", ActivityScope.LINE, PlanType.PREPAID, RequirementClass.REQUIRED),
    ActivityDefinition("NETWORK_VALIDATION", ActivityScope.LINE, PlanType.POSTPAID, RequirementClass.REQUIRED),
    ActivityDefinition("NETWORK_VALIDATION", ActivityScope.LINE, PlanType.PREPAID, RequirementClass.REQUIRED),
    ActivityDefinition("ACCOUNT_SECURITY", ActivityScope.ACCOUNT, PlanType.POSTPAID, RequirementClass.REQUIRED),
    ActivityDefinition("ACCOUNT_SECURITY", ActivityScope.ACCOUNT, PlanType.PREPAID, RequirementClass.REQUIRED),
    ActivityDefinition("APP_ADOPTION", ActivityScope.LINE, PlanType.POSTPAID, RequirementClass.RECOMMENDED),
    ActivityDefinition("APP_ADOPTION", ActivityScope.LINE, PlanType.PREPAID, RequirementClass.RECOMMENDED),
    ActivityDefinition("VOICEMAIL_SETUP", ActivityScope.LINE, PlanType.POSTPAID, RequirementClass.RECOMMENDED),
    ActivityDefinition("VOICEMAIL_SETUP", ActivityScope.LINE, PlanType.PREPAID, RequirementClass.RECOMMENDED),
    ActivityDefinition(
        "AUTOPAY_PAYMENT_SETUP", ActivityScope.ACCOUNT, PlanType.POSTPAID, RequirementClass.RECOMMENDED
    ),
    ActivityDefinition("PAPERLESS_BILLING", ActivityScope.ACCOUNT, PlanType.POSTPAID, RequirementClass.RECOMMENDED),
    ActivityDefinition(
        "FIRST_BILL_READINESS", ActivityScope.ACCOUNT, PlanType.POSTPAID, RequirementClass.RECOMMENDED
    ),
    ActivityDefinition("PAYMENT_METHOD_SETUP", ActivityScope.ACCOUNT, PlanType.PREPAID, RequirementClass.RECOMMENDED),
    ActivityDefinition("AUTO_RECHARGE_SETUP", ActivityScope.LINE, PlanType.PREPAID, RequirementClass.RECOMMENDED),
    ActivityDefinition(
        "PLAN_DATA_USAGE_UNDERSTANDING", ActivityScope.LINE, PlanType.PREPAID, RequirementClass.RECOMMENDED
    ),
    ActivityDefinition(
        "BALANCE_RENEWAL_READINESS", ActivityScope.LINE, PlanType.PREPAID, RequirementClass.RECOMMENDED
    ),
    ActivityDefinition(
        "DEVICE_PROTECTION_DECISION", ActivityScope.LINE, PlanType.POSTPAID, RequirementClass.OPTIONAL
    ),
    ActivityDefinition("DEVICE_PROTECTION_DECISION", ActivityScope.LINE, PlanType.PREPAID, RequirementClass.OPTIONAL),
    ActivityDefinition("PREMIUM_FEATURE_ADOPTION", ActivityScope.LINE, PlanType.POSTPAID, RequirementClass.OPTIONAL),
    ActivityDefinition("PREMIUM_FEATURE_ADOPTION", ActivityScope.LINE, PlanType.PREPAID, RequirementClass.OPTIONAL),
)

# Activities whose applicability depends on order-level context (e.g. was a
# port actually requested) rather than being unconditionally instantiated.
CONDITIONALLY_APPLICABLE_ACTIVITY_CODES = frozenset({"NUMBER_TRANSFER"})


def activities_for_plan_type(plan_type: PlanType) -> list[ActivityDefinition]:
    """Every ActivityDefinition applicable to the given plan type."""
    return [d for d in _CATALOG if d.plan_type == plan_type]


def get_activity_definition(activity_code: str, plan_type: PlanType) -> ActivityDefinition | None:
    for definition in _CATALOG:
        if definition.activity_code == activity_code and definition.plan_type == plan_type:
            return definition
    return None


def all_activity_codes() -> set[str]:
    return {d.activity_code for d in _CATALOG}


def scope_for_activity_code(activity_code: str) -> ActivityScope:
    """Scope is consistent across plan types for a given activity_code."""
    for definition in _CATALOG:
        if definition.activity_code == activity_code:
            return definition.scope
    raise KeyError(f"unknown activity_code: {activity_code}")
