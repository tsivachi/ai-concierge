from concierge.decisioning.health_score import compute_account_health_score, compute_line_health_score
from concierge.decisioning.models import ActivitySnapshot, FrictionFlags
from concierge.domain.enums import ActivityStatus, RequirementClass


def _snap(code, status, req=RequirementClass.REQUIRED):
    return ActivitySnapshot(activity_code=code, requirement_class=req, status=status)


def _all_healthy_activities():
    return [
        _snap("SIM_ESIM_ACTIVATION", ActivityStatus.COMPLETED),
        _snap("NETWORK_VALIDATION", ActivityStatus.COMPLETED),
        _snap("NUMBER_TRANSFER", ActivityStatus.NOT_APPLICABLE),
        _snap("ACCOUNT_SECURITY", ActivityStatus.COMPLETED),
        _snap("APP_ADOPTION", ActivityStatus.COMPLETED, RequirementClass.RECOMMENDED),
        _snap("AUTOPAY_PAYMENT_SETUP", ActivityStatus.COMPLETED, RequirementClass.RECOMMENDED),
    ]


def test_fully_healthy_line_scores_100_green():
    result = compute_line_health_score(_all_healthy_activities(), FrictionFlags())
    assert result.score == 100
    assert result.band == "GREEN"
    assert result.reason_codes == []


def test_activation_incomplete_deducts_30():
    activities = _all_healthy_activities()
    activities[0] = _snap("SIM_ESIM_ACTIVATION", ActivityStatus.IN_PROGRESS)
    result = compute_line_health_score(activities, FrictionFlags())
    assert result.score == 70
    assert {"code": "ACTIVATION_INCOMPLETE", "label": "Activation incomplete", "deduction": -30} in result.reason_codes


def test_activation_failure_deducts_25():
    activities = _all_healthy_activities()
    activities[0] = _snap("SIM_ESIM_ACTIVATION", ActivityStatus.FAILED)
    result = compute_line_health_score(activities, FrictionFlags())
    assert result.score == 75
    assert any(rc["code"] == "ACTIVATION_FAILURE" for rc in result.reason_codes)


def test_port_pending_too_long_deducts_20():
    activities = _all_healthy_activities()
    activities[2] = _snap("NUMBER_TRANSFER", ActivityStatus.IN_PROGRESS)
    result = compute_line_health_score(activities, FrictionFlags(port_pending_too_long=True))
    assert result.score == 80
    assert any(rc["code"] == "PORT_PENDING_TOO_LONG" for rc in result.reason_codes)


def test_repeated_help_visits_deducts_10():
    result = compute_line_health_score(_all_healthy_activities(), FrictionFlags(repeated_help_visit=True))
    assert result.score == 90
    assert any(rc["code"] == "REPEATED_HELP_VISITS" for rc in result.reason_codes)


def test_unresolved_repeated_chats_deducts_10():
    result = compute_line_health_score(_all_healthy_activities(), FrictionFlags(unresolved_repeated_chat=True))
    assert result.score == 90
    assert any(rc["code"] == "UNRESOLVED_REPEATED_CHATS" for rc in result.reason_codes)


def test_required_setup_incomplete_deducts_10():
    activities = _all_healthy_activities()
    activities[3] = _snap("ACCOUNT_SECURITY", ActivityStatus.NOT_STARTED)
    result = compute_line_health_score(activities, FrictionFlags())
    assert result.score == 90
    assert any(rc["code"] == "REQUIRED_SETUP_INCOMPLETE" for rc in result.reason_codes)


def test_setup_step_abandoned_deducts_10():
    result = compute_line_health_score(
        _all_healthy_activities(), FrictionFlags(setup_abandoned_activity_codes=frozenset({"APP_ADOPTION"}))
    )
    assert result.score == 90
    assert any(rc["code"] == "SETUP_STEP_ABANDONED" for rc in result.reason_codes)


def test_app_not_adopted_deducts_5():
    activities = _all_healthy_activities()
    activities[4] = _snap("APP_ADOPTION", ActivityStatus.NOT_STARTED, RequirementClass.RECOMMENDED)
    result = compute_line_health_score(activities, FrictionFlags())
    assert result.score == 95
    assert any(rc["code"] == "APP_NOT_ADOPTED" for rc in result.reason_codes)


def test_autopay_incomplete_deducts_5():
    activities = _all_healthy_activities()
    activities[5] = _snap("AUTOPAY_PAYMENT_SETUP", ActivityStatus.NOT_STARTED, RequirementClass.RECOMMENDED)
    result = compute_line_health_score(activities, FrictionFlags())
    assert result.score == 95
    assert any(rc["code"] == "AUTOPAY_AUTO_RECHARGE_INCOMPLETE" for rc in result.reason_codes)


def test_score_clamps_at_zero_when_every_deduction_applies():
    # Every deduction FR-016 defines stacks to exactly -100 (ACTIVATION_INCOMPLETE
    # is mutually exclusive with ACTIVATION_FAILURE on the same activity, so this
    # is the true maximum achievable, exercising the clamp boundary exactly.
    activities = [
        _snap("SIM_ESIM_ACTIVATION", ActivityStatus.IN_PROGRESS),
        _snap("NETWORK_VALIDATION", ActivityStatus.NOT_STARTED),
        _snap("NUMBER_TRANSFER", ActivityStatus.IN_PROGRESS),
        _snap("ACCOUNT_SECURITY", ActivityStatus.NOT_STARTED),
        _snap("APP_ADOPTION", ActivityStatus.NOT_STARTED, RequirementClass.RECOMMENDED),
        _snap("AUTOPAY_PAYMENT_SETUP", ActivityStatus.NOT_STARTED, RequirementClass.RECOMMENDED),
    ]
    result = compute_line_health_score(
        activities,
        FrictionFlags(
            port_pending_too_long=True,
            repeated_help_visit=True,
            unresolved_repeated_chat=True,
            setup_abandoned_activity_codes=frozenset({"APP_ADOPTION"}),
        ),
    )
    assert result.score == 0
    assert result.band == "RED"
    # Every applicable deduction is still listed even though clamping hides the raw sum (CHK024).
    codes = {rc["code"] for rc in result.reason_codes}
    assert "ACTIVATION_INCOMPLETE" in codes
    assert "REPEATED_HELP_VISITS" in codes


def test_score_clamps_at_zero_never_goes_negative():
    activities = [
        _snap("SIM_ESIM_ACTIVATION", ActivityStatus.FAILED),
        _snap("NETWORK_VALIDATION", ActivityStatus.FAILED),
        _snap("NUMBER_TRANSFER", ActivityStatus.FAILED),
        _snap("ACCOUNT_SECURITY", ActivityStatus.NOT_STARTED),
        _snap("APP_ADOPTION", ActivityStatus.NOT_STARTED, RequirementClass.RECOMMENDED),
        _snap("AUTOPAY_PAYMENT_SETUP", ActivityStatus.NOT_STARTED, RequirementClass.RECOMMENDED),
    ]
    result = compute_line_health_score(
        activities,
        FrictionFlags(
            repeated_help_visit=True,
            unresolved_repeated_chat=True,
            setup_abandoned_activity_codes=frozenset({"APP_ADOPTION"}),
        ),
    )
    assert result.score >= 0


def test_health_band_thresholds():
    assert compute_line_health_score(_all_healthy_activities(), FrictionFlags()).band == "GREEN"

    activities = _all_healthy_activities()
    activities[0] = _snap("SIM_ESIM_ACTIVATION", ActivityStatus.FAILED)  # -25 -> 75, still GREEN boundary
    assert compute_line_health_score(activities, FrictionFlags()).score == 75


def test_account_score_is_minimum_of_line_scores():
    score, band = compute_account_health_score([90, 55, 100])
    assert score == 55
    assert band == "YELLOW"


def test_account_score_defaults_to_100_with_no_lines():
    score, band = compute_account_health_score([])
    assert score == 100
    assert band == "GREEN"
