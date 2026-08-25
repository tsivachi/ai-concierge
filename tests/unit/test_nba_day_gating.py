import pytest

from concierge.decisioning.models import ActivitySnapshot
from concierge.decisioning.nba import (
    APP_GAP_DAY_THRESHOLD,
    AUTOPAY_GAP_DAY_THRESHOLD,
    PROTECTION_DECISION_DAY_THRESHOLD,
    VOICEMAIL_GAP_DAY_THRESHOLD,
    generate_candidates,
)
from concierge.domain.enums import ActivityStatus, RequirementClass


def _snap(code, status, req=RequirementClass.RECOMMENDED):
    return ActivitySnapshot(activity_code=code, requirement_class=req, status=status)


@pytest.mark.parametrize(
    "activity_code,action_code,threshold",
    [
        ("APP_ADOPTION", "APP_GAP", APP_GAP_DAY_THRESHOLD),
        ("VOICEMAIL_SETUP", "VOICEMAIL_GAP", VOICEMAIL_GAP_DAY_THRESHOLD),
    ],
)
def test_recommended_activity_gap_absent_before_and_present_after_threshold(activity_code, action_code, threshold):
    activities = [_snap(activity_code, ActivityStatus.NOT_STARTED)]

    before = generate_candidates("line-1", activities, journey_day=threshold)
    assert not any(c.action_code == action_code for c in before)

    after = generate_candidates("line-1", activities, journey_day=threshold + 1)
    assert any(c.action_code == action_code for c in after)


def test_autopay_gap_requires_day_threshold():
    activities = [_snap("AUTOPAY_PAYMENT_SETUP", ActivityStatus.NOT_STARTED)]

    before = generate_candidates("line-1", activities, journey_day=AUTOPAY_GAP_DAY_THRESHOLD)
    assert not any(c.action_code == "AUTOPAY_AUTO_RECHARGE_GAP" for c in before)

    after = generate_candidates("line-1", activities, journey_day=AUTOPAY_GAP_DAY_THRESHOLD + 1)
    assert any(c.action_code == "AUTOPAY_AUTO_RECHARGE_GAP" for c in after)


def test_auto_recharge_gap_uses_the_same_threshold_as_autopay():
    activities = [_snap("AUTO_RECHARGE_SETUP", ActivityStatus.NOT_STARTED)]
    after = generate_candidates("line-1", activities, journey_day=AUTOPAY_GAP_DAY_THRESHOLD + 1)
    assert any(c.action_code == "AUTOPAY_AUTO_RECHARGE_GAP" for c in after)


def test_protection_decision_gap_requires_day_threshold():
    activities = [_snap("DEVICE_PROTECTION_DECISION", ActivityStatus.NOT_STARTED, RequirementClass.OPTIONAL)]

    before = generate_candidates("line-1", activities, journey_day=PROTECTION_DECISION_DAY_THRESHOLD)
    assert not any(c.action_code == "PROTECTION_DECISION_GAP" for c in before)

    after = generate_candidates("line-1", activities, journey_day=PROTECTION_DECISION_DAY_THRESHOLD + 1)
    assert any(c.action_code == "PROTECTION_DECISION_GAP" for c in after)


def test_gap_clears_once_activity_completed_regardless_of_day():
    activities = [_snap("APP_ADOPTION", ActivityStatus.COMPLETED)]
    candidates = generate_candidates("line-1", activities, journey_day=APP_GAP_DAY_THRESHOLD + 30)
    assert not any(c.action_code == "APP_GAP" for c in candidates)
