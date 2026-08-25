"""FR-005: line/account completion derivation. Pure functions, no DB."""

from datetime import datetime, timedelta, timezone

from concierge.journey.status import ActivityStatusView, derive_journey_status, is_line_complete


def _view(code, status, req="REQUIRED"):
    return ActivityStatusView(activity_code=code, status=status, requirement_class=req)


def test_line_complete_when_all_required_completed():
    line = [_view("SIM_ESIM_ACTIVATION", "COMPLETED"), _view("APP_ADOPTION", "NOT_STARTED", "RECOMMENDED")]
    account = [_view("ACCOUNT_SECURITY", "COMPLETED")]
    assert is_line_complete(line, account) is True


def test_line_not_complete_with_open_required_activity():
    line = [_view("SIM_ESIM_ACTIVATION", "IN_PROGRESS")]
    account = [_view("ACCOUNT_SECURITY", "COMPLETED")]
    assert is_line_complete(line, account) is False


def test_line_complete_with_not_applicable_required_activity():
    line = [_view("SIM_ESIM_ACTIVATION", "COMPLETED"), _view("NUMBER_TRANSFER", "NOT_APPLICABLE")]
    account = [_view("ACCOUNT_SECURITY", "COMPLETED")]
    assert is_line_complete(line, account) is True


def test_recommended_and_optional_activities_never_block_completion():
    line = [
        _view("SIM_ESIM_ACTIVATION", "COMPLETED"),
        _view("APP_ADOPTION", "NOT_STARTED", "RECOMMENDED"),
        _view("PREMIUM_FEATURE_ADOPTION", "NOT_STARTED", "OPTIONAL"),
    ]
    account = [_view("ACCOUNT_SECURITY", "COMPLETED")]
    assert is_line_complete(line, account) is True


def test_account_scoped_required_activity_blocks_completion_too():
    line = [_view("SIM_ESIM_ACTIVATION", "COMPLETED")]
    account = [_view("ACCOUNT_SECURITY", "NOT_STARTED")]
    assert is_line_complete(line, account) is False


def test_journey_status_active_when_not_all_lines_complete():
    future = datetime.now(timezone.utc) + timedelta(days=10)
    assert derive_journey_status([True, False], future) == "ACTIVE"


def test_journey_status_complete_when_every_line_complete():
    future = datetime.now(timezone.utc) + timedelta(days=10)
    assert derive_journey_status([True, True], future) == "COMPLETE"


def test_journey_status_complete_takes_priority_over_expiry():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    assert derive_journey_status([True], past) == "COMPLETE"


def test_journey_status_expired_when_incomplete_past_expiry():
    past = datetime.now(timezone.utc) - timedelta(days=1)
    assert derive_journey_status([False], past) == "EXPIRED"


def test_journey_status_active_with_no_lines_yet():
    future = datetime.now(timezone.utc) + timedelta(days=10)
    assert derive_journey_status([], future) == "ACTIVE"
