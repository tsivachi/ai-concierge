"""Health-score computation (FR-016, FR-017, FR-018). Pure function: takes a
line's activity snapshots plus friction signals, returns a clamped 0-100
score, its band, and the full list of reason codes for every deduction
applied — never only the deductions that survive clamping (spec.md
Assumptions / checklist CHK024).

Deduction-to-condition mapping (spec.md Assumptions, CHK023): "incomplete"
means not yet COMPLETED/FAILED (still NOT_STARTED/IN_PROGRESS); "failure"
means FAILED. Where FR-016 has no dedicated deduction for a specific
REQUIRED activity (network/port failure), the closest documented deduction
is reused rather than inventing a new one.
"""

from concierge.domain.enums import ActivityStatus, RequirementClass, health_band_for_score
from concierge.decisioning.models import ActivitySnapshot, FrictionFlags, HealthScoreResult

_MIN_SCORE = 0
_MAX_SCORE = 100

_CORE_ACTIVATION_CODES = ("SIM_ESIM_ACTIVATION", "NETWORK_VALIDATION")
_AUTOPAY_LIKE_CODES = ("AUTOPAY_PAYMENT_SETUP", "AUTO_RECHARGE_SETUP")
# REQUIRED activities with a dedicated deduction of their own — everything
# else REQUIRED/applicable-and-incomplete falls under REQUIRED_SETUP_INCOMPLETE.
_SPECIALLY_HANDLED_REQUIRED_CODES = frozenset({"SIM_ESIM_ACTIVATION", "NETWORK_VALIDATION", "NUMBER_TRANSFER"})


def _by_code(activities: list[ActivitySnapshot]) -> dict[str, ActivitySnapshot]:
    return {a.activity_code: a for a in activities}


def compute_line_health_score(activities: list[ActivitySnapshot], friction: FrictionFlags) -> HealthScoreResult:
    by_code = _by_code(activities)
    deductions: list[dict] = []

    # ACTIVATION_INCOMPLETE (-30): core device activation not yet finished.
    sim = by_code.get("SIM_ESIM_ACTIVATION")
    if sim is not None and sim.status in (ActivityStatus.NOT_STARTED, ActivityStatus.IN_PROGRESS):
        deductions.append({"code": "ACTIVATION_INCOMPLETE", "label": "Activation incomplete", "deduction": -30})

    # ACTIVATION_FAILURE (-25): the activation cluster (SIM/eSIM or network) failed.
    if any(by_code.get(code) is not None and by_code[code].status == ActivityStatus.FAILED for code in _CORE_ACTIVATION_CODES):
        deductions.append({"code": "ACTIVATION_FAILURE", "label": "Activation failure", "deduction": -25})

    # PORT_PENDING_TOO_LONG (-20): number transfer stuck or failed.
    port = by_code.get("NUMBER_TRANSFER")
    if port is not None and port.status != ActivityStatus.NOT_APPLICABLE:
        if port.status == ActivityStatus.FAILED or friction.port_pending_too_long:
            deductions.append(
                {"code": "PORT_PENDING_TOO_LONG", "label": "Port pending too long", "deduction": -20}
            )

    if friction.repeated_help_visit:
        deductions.append(
            {"code": "REPEATED_HELP_VISITS", "label": "Repeated help visits", "deduction": -10}
        )

    if friction.unresolved_repeated_chat:
        deductions.append(
            {"code": "UNRESOLVED_REPEATED_CHATS", "label": "Unresolved repeated chats", "deduction": -10}
        )

    # REQUIRED_SETUP_INCOMPLETE (-10): any other REQUIRED, applicable activity not COMPLETED.
    other_required_incomplete = any(
        a.requirement_class == RequirementClass.REQUIRED
        and a.activity_code not in _SPECIALLY_HANDLED_REQUIRED_CODES
        and a.status not in (ActivityStatus.COMPLETED, ActivityStatus.NOT_APPLICABLE)
        for a in activities
    )
    if other_required_incomplete:
        deductions.append(
            {"code": "REQUIRED_SETUP_INCOMPLETE", "label": "Required setup incomplete", "deduction": -10}
        )

    if friction.setup_abandoned_activity_codes:
        deductions.append(
            {"code": "SETUP_STEP_ABANDONED", "label": "Setup step abandoned", "deduction": -10}
        )

    app = by_code.get("APP_ADOPTION")
    if app is not None and app.status != ActivityStatus.COMPLETED:
        deductions.append({"code": "APP_NOT_ADOPTED", "label": "App not adopted", "deduction": -5})

    autopay_like = [by_code[c] for c in _AUTOPAY_LIKE_CODES if c in by_code]
    if autopay_like and all(a.status != ActivityStatus.COMPLETED for a in autopay_like):
        deductions.append(
            {
                "code": "AUTOPAY_AUTO_RECHARGE_INCOMPLETE",
                "label": "AutoPay/auto-recharge incomplete",
                "deduction": -5,
            }
        )

    raw_score = _MAX_SCORE + sum(d["deduction"] for d in deductions)
    clamped_score = max(_MIN_SCORE, min(_MAX_SCORE, raw_score))
    band = health_band_for_score(clamped_score).value

    return HealthScoreResult(score=clamped_score, band=band, reason_codes=deductions)


def compute_account_health_score(line_scores: list[int]) -> tuple[int, str]:
    """The account-level score is the minimum of its lines' scores
    (data-model.md §HealthScoreRecord) — the account never reads healthier
    than its worst line."""
    score = min(line_scores) if line_scores else _MAX_SCORE
    return score, health_band_for_score(score).value
