from concierge.domain.enums import ActivityScope, PlanType, RequirementClass
from concierge.journey.activity_catalog import (
    activities_for_plan_type,
    all_activity_codes,
    get_activity_definition,
    scope_for_activity_code,
)

# Expected per data-model.md §ActivityDefinition (research.md §10).
EXPECTED_POSTPAID = {
    "SIM_ESIM_ACTIVATION": RequirementClass.REQUIRED,
    "NUMBER_TRANSFER": RequirementClass.REQUIRED,
    "NETWORK_VALIDATION": RequirementClass.REQUIRED,
    "ACCOUNT_SECURITY": RequirementClass.REQUIRED,
    "APP_ADOPTION": RequirementClass.RECOMMENDED,
    "VOICEMAIL_SETUP": RequirementClass.RECOMMENDED,
    "AUTOPAY_PAYMENT_SETUP": RequirementClass.RECOMMENDED,
    "PAPERLESS_BILLING": RequirementClass.RECOMMENDED,
    "FIRST_BILL_READINESS": RequirementClass.RECOMMENDED,
    "DEVICE_PROTECTION_DECISION": RequirementClass.OPTIONAL,
    "PREMIUM_FEATURE_ADOPTION": RequirementClass.OPTIONAL,
}

EXPECTED_PREPAID = {
    "SIM_ESIM_ACTIVATION": RequirementClass.REQUIRED,
    "NUMBER_TRANSFER": RequirementClass.REQUIRED,
    "NETWORK_VALIDATION": RequirementClass.REQUIRED,
    "ACCOUNT_SECURITY": RequirementClass.REQUIRED,
    "APP_ADOPTION": RequirementClass.RECOMMENDED,
    "VOICEMAIL_SETUP": RequirementClass.RECOMMENDED,
    "PAYMENT_METHOD_SETUP": RequirementClass.RECOMMENDED,
    "AUTO_RECHARGE_SETUP": RequirementClass.RECOMMENDED,
    "PLAN_DATA_USAGE_UNDERSTANDING": RequirementClass.RECOMMENDED,
    "BALANCE_RENEWAL_READINESS": RequirementClass.RECOMMENDED,
    "DEVICE_PROTECTION_DECISION": RequirementClass.OPTIONAL,
    "PREMIUM_FEATURE_ADOPTION": RequirementClass.OPTIONAL,
}


def test_postpaid_catalog_matches_expected_classification():
    catalog = {d.activity_code: d.requirement_class for d in activities_for_plan_type(PlanType.POSTPAID)}
    assert catalog == EXPECTED_POSTPAID


def test_prepaid_catalog_matches_expected_classification():
    catalog = {d.activity_code: d.requirement_class for d in activities_for_plan_type(PlanType.PREPAID)}
    assert catalog == EXPECTED_PREPAID


def test_postpaid_only_activities_absent_from_prepaid():
    prepaid_codes = {d.activity_code for d in activities_for_plan_type(PlanType.PREPAID)}
    for code in ("AUTOPAY_PAYMENT_SETUP", "PAPERLESS_BILLING", "FIRST_BILL_READINESS"):
        assert code not in prepaid_codes


def test_prepaid_only_activities_absent_from_postpaid():
    postpaid_codes = {d.activity_code for d in activities_for_plan_type(PlanType.POSTPAID)}
    for code in (
        "PAYMENT_METHOD_SETUP",
        "AUTO_RECHARGE_SETUP",
        "PLAN_DATA_USAGE_UNDERSTANDING",
        "BALANCE_RENEWAL_READINESS",
    ):
        assert code not in postpaid_codes


def test_every_required_activity_is_line_or_account_scoped_correctly():
    assert scope_for_activity_code("ACCOUNT_SECURITY") == ActivityScope.ACCOUNT
    assert scope_for_activity_code("SIM_ESIM_ACTIVATION") == ActivityScope.LINE
    assert scope_for_activity_code("AUTOPAY_PAYMENT_SETUP") == ActivityScope.ACCOUNT
    assert scope_for_activity_code("AUTO_RECHARGE_SETUP") == ActivityScope.LINE


def test_get_activity_definition_returns_none_for_unknown_combination():
    assert get_activity_definition("AUTOPAY_PAYMENT_SETUP", PlanType.PREPAID) is None
    assert get_activity_definition("SIM_ESIM_ACTIVATION", PlanType.POSTPAID) is not None


def test_all_activity_codes_covers_every_catalog_entry():
    codes = all_activity_codes()
    assert "PAPERLESS_BILLING" in codes
    assert "BALANCE_RENEWAL_READINESS" in codes
    assert len(codes) == len(set(EXPECTED_POSTPAID) | set(EXPECTED_PREPAID))
