"""Pure functions mapping (activity_code, current_status, event_type) -> new_status.

No I/O here — this module is unit-testable without a database (Constitution
Principle I: deterministic core, zero side effects).
"""

from concierge.domain.enums import TERMINAL_ACTIVITY_STATUSES, ActivityStatus

# Which event moves a given activity to which status. Activities with no
# entry here have no event-driven transition in this MVP (e.g. paperless
# billing, first-bill readiness, payment method setup, plan/data usage
# understanding, balance/renewal readiness, device protection decision,
# premium feature adoption) — they are RECOMMENDED/OPTIONAL and don't block
# onboarding completion (FR-005) regardless.
_TRANSITION_RULES: dict[str, dict[str, ActivityStatus]] = {
    "SIM_ESIM_ACTIVATION": {
        "DeviceActivationStarted": ActivityStatus.IN_PROGRESS,
        "DeviceActivationCompleted": ActivityStatus.COMPLETED,
        "DeviceActivationFailed": ActivityStatus.FAILED,
    },
    "NETWORK_VALIDATION": {
        # No dedicated "network validated" event exists in the FR-006 catalog;
        # a successful device activation implies the device reached the
        # network, so it drives this activity too (simplest local-first choice).
        "DeviceActivationStarted": ActivityStatus.IN_PROGRESS,
        "DeviceActivationCompleted": ActivityStatus.COMPLETED,
        "DeviceActivationFailed": ActivityStatus.FAILED,
    },
    "NUMBER_TRANSFER": {
        "NumberTransferRequested": ActivityStatus.IN_PROGRESS,
        "NumberTransferPending": ActivityStatus.IN_PROGRESS,
        "NumberTransferCompleted": ActivityStatus.COMPLETED,
        "NumberTransferFailed": ActivityStatus.FAILED,
    },
    "ACCOUNT_SECURITY": {
        # No dedicated security-setup event exists either; first login is the
        # simplest local-first proxy for "the account's security step is done."
        "CustomerLoggedIn": ActivityStatus.COMPLETED,
    },
    "APP_ADOPTION": {"MobileAppDownloaded": ActivityStatus.COMPLETED},
    "VOICEMAIL_SETUP": {"VoicemailConfigured": ActivityStatus.COMPLETED},
    "AUTOPAY_PAYMENT_SETUP": {"AutoPayEnabled": ActivityStatus.COMPLETED},
    "AUTO_RECHARGE_SETUP": {"AutoRechargeEnabled": ActivityStatus.COMPLETED},
}


def activity_codes_for_event(event_type: str) -> list[str]:
    """Every activity_code with a transition rule for this event_type."""
    return [code for code, rules in _TRANSITION_RULES.items() if event_type in rules]


def next_status_for_event(
    activity_code: str, current_status: ActivityStatus, event_type: str
) -> ActivityStatus | None:
    """Returns the status this event would move the activity to, or None if
    the event doesn't affect this activity, or the activity is already in a
    terminal status (COMPLETED/NOT_APPLICABLE never transition further —
    the "clear terminal-state rule" required by spec.md Edge Cases)."""
    if current_status in TERMINAL_ACTIVITY_STATUSES:
        return None

    rules = _TRANSITION_RULES.get(activity_code)
    if rules is None:
        return None

    return rules.get(event_type)
