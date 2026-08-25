from concierge.decisioning.escalation import (
    billing_dispute_trigger,
    explicit_request_trigger,
    sensitive_security_trigger,
    two_failed_troubleshooting_trigger,
    unresolved_activation_or_port_trigger,
    unsupported_low_confidence_trigger,
)
from concierge.decisioning.models import ActivitySnapshot
from concierge.domain.enums import ActivityStatus, RequirementClass


def _snap(code, status):
    return ActivitySnapshot(activity_code=code, requirement_class=RequirementClass.REQUIRED, status=status)


def test_explicit_request_trigger_fires_on_human_request_phrasing():
    assert explicit_request_trigger("can I talk to a human?") is True
    assert explicit_request_trigger("I need to speak with a representative") is True


def test_explicit_request_trigger_does_not_fire_on_ordinary_question():
    assert explicit_request_trigger("how do I set up voicemail?") is False


def test_billing_dispute_trigger_fires_on_dispute_language():
    assert billing_dispute_trigger("I was overcharged this month") is True
    assert billing_dispute_trigger("this charge is wrong") is True


def test_billing_dispute_trigger_does_not_fire_on_ordinary_billing_question():
    assert billing_dispute_trigger("what does my bill include?") is False


def test_sensitive_security_trigger_fires_on_unauthorized_activity_language():
    assert sensitive_security_trigger("someone ported my number without my permission") is True
    assert sensitive_security_trigger("I think my account was hacked") is True


def test_sensitive_security_trigger_does_not_fire_on_ordinary_security_question():
    assert sensitive_security_trigger("how do I set an account PIN?") is False


def test_two_failed_troubleshooting_trigger_fires_at_threshold():
    assert two_failed_troubleshooting_trigger(2) is True
    assert two_failed_troubleshooting_trigger(1) is False
    assert two_failed_troubleshooting_trigger(0) is False


def test_unsupported_low_confidence_trigger_fires_on_zero_sources():
    assert unsupported_low_confidence_trigger(retrieved_source_count=0, requested_unsupported_action=False) is True


def test_unsupported_low_confidence_trigger_fires_on_unsupported_action():
    assert unsupported_low_confidence_trigger(retrieved_source_count=3, requested_unsupported_action=True) is True


def test_unsupported_low_confidence_trigger_does_not_fire_with_sources_and_supported_request():
    assert unsupported_low_confidence_trigger(retrieved_source_count=2, requested_unsupported_action=False) is False


def test_unresolved_activation_or_port_trigger_returns_action_code_for_failed_activation():
    activities = [_snap("SIM_ESIM_ACTIVATION", ActivityStatus.FAILED)]
    assert unresolved_activation_or_port_trigger(activities) == "ACTIVATION_FAILURE"


def test_unresolved_activation_or_port_trigger_returns_action_code_for_failed_port():
    activities = [_snap("NUMBER_TRANSFER", ActivityStatus.FAILED)]
    assert unresolved_activation_or_port_trigger(activities) == "NUMBER_TRANSFER_FAILURE"


def test_unresolved_activation_or_port_trigger_returns_action_code_for_failed_network():
    activities = [_snap("NETWORK_VALIDATION", ActivityStatus.FAILED)]
    assert unresolved_activation_or_port_trigger(activities) == "NETWORK_FAILURE"


def test_unresolved_activation_or_port_trigger_returns_none_when_all_healthy():
    activities = [
        _snap("SIM_ESIM_ACTIVATION", ActivityStatus.COMPLETED),
        _snap("NETWORK_VALIDATION", ActivityStatus.COMPLETED),
        _snap("NUMBER_TRANSFER", ActivityStatus.NOT_APPLICABLE),
    ]
    assert unresolved_activation_or_port_trigger(activities) is None


def test_unresolved_activation_or_port_trigger_ignores_in_progress_status():
    activities = [_snap("SIM_ESIM_ACTIVATION", ActivityStatus.IN_PROGRESS)]
    assert unresolved_activation_or_port_trigger(activities) is None
