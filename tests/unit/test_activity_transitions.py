from concierge.domain.enums import ActivityStatus
from concierge.journey.transitions import activity_codes_for_event, next_status_for_event


def test_activation_started_moves_not_started_to_in_progress():
    result = next_status_for_event("SIM_ESIM_ACTIVATION", ActivityStatus.NOT_STARTED, "DeviceActivationStarted")
    assert result == ActivityStatus.IN_PROGRESS


def test_activation_completed_moves_in_progress_to_completed():
    result = next_status_for_event("SIM_ESIM_ACTIVATION", ActivityStatus.IN_PROGRESS, "DeviceActivationCompleted")
    assert result == ActivityStatus.COMPLETED


def test_activation_failed_moves_in_progress_to_failed():
    result = next_status_for_event("SIM_ESIM_ACTIVATION", ActivityStatus.IN_PROGRESS, "DeviceActivationFailed")
    assert result == ActivityStatus.FAILED


def test_retry_after_failure_can_reach_completed():
    # FAILED is not terminal — a retry (Started -> Completed) must still work (US2 AC2).
    status = ActivityStatus.FAILED
    status = next_status_for_event("SIM_ESIM_ACTIVATION", status, "DeviceActivationStarted")
    assert status == ActivityStatus.IN_PROGRESS
    status = next_status_for_event("SIM_ESIM_ACTIVATION", status, "DeviceActivationCompleted")
    assert status == ActivityStatus.COMPLETED


def test_terminal_completed_status_never_transitions_again():
    result = next_status_for_event("SIM_ESIM_ACTIVATION", ActivityStatus.COMPLETED, "DeviceActivationFailed")
    assert result is None


def test_terminal_not_applicable_status_never_transitions():
    result = next_status_for_event("NUMBER_TRANSFER", ActivityStatus.NOT_APPLICABLE, "NumberTransferCompleted")
    assert result is None


def test_unrelated_event_does_not_affect_activity():
    result = next_status_for_event("VOICEMAIL_SETUP", ActivityStatus.NOT_STARTED, "AutoPayEnabled")
    assert result is None


def test_activity_without_any_transition_rule_returns_none():
    result = next_status_for_event("PAPERLESS_BILLING", ActivityStatus.NOT_STARTED, "DeviceActivationCompleted")
    assert result is None


def test_number_transfer_full_lifecycle():
    status = ActivityStatus.NOT_STARTED
    for event_type, expected in (
        ("NumberTransferRequested", ActivityStatus.IN_PROGRESS),
        ("NumberTransferPending", ActivityStatus.IN_PROGRESS),
        ("NumberTransferCompleted", ActivityStatus.COMPLETED),
    ):
        status = next_status_for_event("NUMBER_TRANSFER", status, event_type)
        assert status == expected


def test_activity_codes_for_event_returns_every_affected_activity():
    codes = set(activity_codes_for_event("DeviceActivationCompleted"))
    assert codes == {"SIM_ESIM_ACTIVATION", "NETWORK_VALIDATION"}


def test_activity_codes_for_event_empty_for_unmapped_event():
    assert activity_codes_for_event("HelpArticleViewed") == []
