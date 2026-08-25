from concierge.decisioning.models import ActivitySnapshot
from concierge.decisioning.nba import (
    APP_GAP_DAY_THRESHOLD,
    current_nba_for_line,
    filter_escalation_suppressed,
    generate_candidates,
    rank_candidates,
)
from concierge.domain.enums import ActivityStatus, RequirementClass


def _snap(code, status, req=RequirementClass.REQUIRED):
    return ActivitySnapshot(activity_code=code, requirement_class=req, status=status)


def _base_activities():
    return [
        _snap("SIM_ESIM_ACTIVATION", ActivityStatus.COMPLETED),
        _snap("NETWORK_VALIDATION", ActivityStatus.COMPLETED),
        _snap("NUMBER_TRANSFER", ActivityStatus.NOT_APPLICABLE),
        _snap("ACCOUNT_SECURITY", ActivityStatus.COMPLETED),
        _snap("APP_ADOPTION", ActivityStatus.NOT_STARTED, RequirementClass.RECOMMENDED),
        _snap("VOICEMAIL_SETUP", ActivityStatus.NOT_STARTED, RequirementClass.RECOMMENDED),
    ]


def test_no_candidates_when_everything_healthy_and_before_thresholds():
    candidates = generate_candidates("line-1", _base_activities(), journey_day=1)
    assert candidates == []


def test_activation_failure_outranks_everything():
    activities = _base_activities()
    activities[0] = _snap("SIM_ESIM_ACTIVATION", ActivityStatus.FAILED)
    candidates = generate_candidates("line-1", activities, journey_day=1)
    ranked = rank_candidates(candidates)
    assert ranked[0].action_code == "ACTIVATION_FAILURE"
    assert ranked[0].priority == 100


def test_base_priority_ordering_matches_fr011():
    activities = _base_activities()
    activities[3] = _snap("ACCOUNT_SECURITY", ActivityStatus.NOT_STARTED)
    # Before any day-gated adoption threshold, only the required-setup gap is eligible.
    candidates = generate_candidates("line-1", activities, journey_day=1)
    ranked = rank_candidates(candidates)
    assert [c.action_code for c in ranked] == ["REQUIRED_SECURITY_INCOMPLETE"]
    assert ranked[0].priority == 70


def test_tie_break_order_critical_over_required_setup_over_digital_adoption():
    activities = _base_activities()
    activities[0] = _snap("SIM_ESIM_ACTIVATION", ActivityStatus.FAILED)  # critical
    activities[3] = _snap("ACCOUNT_SECURITY", ActivityStatus.NOT_STARTED)  # required setup
    candidates = generate_candidates("line-1", activities, journey_day=APP_GAP_DAY_THRESHOLD + 1)
    ranked = rank_candidates(candidates)
    codes_in_order = [c.action_code for c in ranked]
    assert codes_in_order.index("ACTIVATION_FAILURE") < codes_in_order.index("REQUIRED_SECURITY_INCOMPLETE")
    assert codes_in_order.index("REQUIRED_SECURITY_INCOMPLETE") < codes_in_order.index("APP_GAP")


def test_number_transfer_failure_beats_app_adoption_gap():
    """US2 AC4: an unresolved number-transfer failure is chosen over an app-adoption gap."""
    activities = _base_activities()
    activities[2] = _snap("NUMBER_TRANSFER", ActivityStatus.FAILED)
    candidates = generate_candidates("line-1", activities, journey_day=APP_GAP_DAY_THRESHOLD + 1)
    ranked = rank_candidates(candidates)
    assert ranked[0].action_code == "NUMBER_TRANSFER_FAILURE"


def test_app_gap_not_eligible_before_day_threshold():
    activities = _base_activities()
    candidates = generate_candidates("line-1", activities, journey_day=APP_GAP_DAY_THRESHOLD)
    assert not any(c.action_code == "APP_GAP" for c in candidates)


def test_app_gap_eligible_after_day_threshold():
    activities = _base_activities()
    candidates = generate_candidates("line-1", activities, journey_day=APP_GAP_DAY_THRESHOLD + 1)
    assert any(c.action_code == "APP_GAP" for c in candidates)


def test_escalation_suppression_filters_out_matching_action_code():
    activities = _base_activities()
    activities[0] = _snap("SIM_ESIM_ACTIVATION", ActivityStatus.FAILED)
    candidates = generate_candidates("line-1", activities, journey_day=1)
    filtered = filter_escalation_suppressed(candidates, frozenset({"ACTIVATION_FAILURE"}))
    assert filtered == []


def test_current_nba_for_line_returns_none_when_nothing_eligible():
    assert current_nba_for_line(_base_activities(), journey_day=1) is None


def test_cross_line_ranking_is_deterministic_for_identical_priority():
    from concierge.decisioning.models import NBACandidate

    a = NBACandidate(line_id="line-b", action_code="ACTIVATION_FAILURE", priority=100, tie_break_rank=0, reason_codes=[])
    b = NBACandidate(line_id="line-a", action_code="ACTIVATION_FAILURE", priority=100, tie_break_rank=0, reason_codes=[])
    ranked = rank_candidates([a, b])
    # Same priority and category -> final deterministic tiebreak by line_id.
    assert [c.line_id for c in ranked] == ["line-a", "line-b"]
