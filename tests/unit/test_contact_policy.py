from datetime import datetime, timezone

from concierge.decisioning.contact_policy import (
    ContactPolicyConfig,
    allocate_outreach,
    is_quiet_hours,
)
from concierge.decisioning.models import NBACandidate

NOON = datetime(2026, 8, 24, 12, 0, tzinfo=timezone.utc)
MIDNIGHT = datetime(2026, 8, 24, 0, 0, tzinfo=timezone.utc)


def _candidate(line_id="line-1", action_code="APP_GAP", priority=50):
    return NBACandidate(line_id=line_id, action_code=action_code, priority=priority, tie_break_rank=3, reason_codes=[])


def test_is_quiet_hours_wraps_midnight():
    config = ContactPolicyConfig()
    assert is_quiet_hours(datetime(2026, 8, 24, 23, 0, tzinfo=timezone.utc), config) is True
    assert is_quiet_hours(MIDNIGHT, config) is True
    assert is_quiet_hours(datetime(2026, 8, 24, 7, 59, tzinfo=timezone.utc), config) is True
    assert is_quiet_hours(datetime(2026, 8, 24, 8, 0, tzinfo=timezone.utc), config) is False
    assert is_quiet_hours(NOON, config) is False


def test_opted_out_suppresses_regardless_of_urgency():
    decisions = allocate_outreach([_candidate(action_code="ACTIVATION_FAILURE", priority=100)], NOON, True, 0, 0)
    assert decisions[0].status == "SUPPRESSED"
    assert decisions[0].suppression_reason == "OPTED_OUT"


def test_quiet_hours_suppresses_all_candidates():
    decisions = allocate_outreach([_candidate(), _candidate(line_id="line-2")], MIDNIGHT, False, 0, 0)
    assert all(d.status == "SUPPRESSED" and d.suppression_reason == "QUIET_HOURS" for d in decisions)


def test_within_caps_is_delivered():
    decisions = allocate_outreach([_candidate()], NOON, False, 0, 0)
    assert decisions[0].status == "DELIVERED"
    assert decisions[0].suppression_reason is None


def test_daily_cap_reached_suppresses_remainder():
    candidates = [_candidate(line_id=f"line-{i}") for i in range(3)]
    decisions = allocate_outreach(candidates, NOON, False, attempts_today=0, attempts_this_week=0)
    statuses = [d.status for d in decisions]
    assert statuses == ["DELIVERED", "DELIVERED", "SUPPRESSED"]
    assert decisions[2].suppression_reason == "DAILY_CAP"


def test_weekly_cap_reached_suppresses_even_within_daily_cap():
    decisions = allocate_outreach([_candidate()], NOON, False, attempts_today=0, attempts_this_week=5)
    assert decisions[0].status == "SUPPRESSED"
    assert decisions[0].suppression_reason == "WEEKLY_CAP"


def test_already_at_daily_cap_suppresses_new_candidate():
    decisions = allocate_outreach([_candidate()], NOON, False, attempts_today=2, attempts_this_week=2)
    assert decisions[0].status == "SUPPRESSED"
    assert decisions[0].suppression_reason == "DAILY_CAP"


def test_outreach_draws_from_all_lines_in_priority_order_until_cap_reached():
    """FR-014: outreach draws from across all lines' eligible actions in
    priority order until the shared cap is reached."""
    candidates = [
        _candidate(line_id="line-low", action_code="APP_GAP", priority=50),
        _candidate(line_id="line-critical", action_code="ACTIVATION_FAILURE", priority=100),
        _candidate(line_id="line-mid", action_code="REQUIRED_SECURITY_INCOMPLETE", priority=70),
    ]
    from concierge.decisioning.nba import rank_candidates

    ranked = rank_candidates(candidates)
    decisions = allocate_outreach(ranked, NOON, False, attempts_today=0, attempts_this_week=0, config=ContactPolicyConfig(max_per_day=2))
    delivered_lines = [d.candidate.line_id for d in decisions if d.status == "DELIVERED"]
    assert delivered_lines == ["line-critical", "line-mid"]
    suppressed = [d for d in decisions if d.status == "SUPPRESSED"]
    assert suppressed[0].candidate.line_id == "line-low"
    assert suppressed[0].suppression_reason == "DAILY_CAP"
