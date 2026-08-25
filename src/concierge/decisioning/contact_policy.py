"""Contact policy (FR-014, FR-015, FR-028a): daily/weekly caps shared across
a customer's lines, quiet hours, consent/opt-out, and escalation suppression.
Pure decision function — callers supply already-counted attempt totals and
already-filtered (escalation-suppressed) candidates.
"""

from dataclasses import dataclass
from datetime import datetime

from concierge.decisioning.models import NBACandidate, OutreachDecision


@dataclass(frozen=True)
class ContactPolicyConfig:
    max_per_day: int = 2
    max_per_week: int = 5
    quiet_hours_start_hour: int = 22  # 10 PM
    quiet_hours_end_hour: int = 8  # 8 AM


DEFAULT_CONTACT_POLICY = ContactPolicyConfig()


def is_quiet_hours(local_time: datetime, config: ContactPolicyConfig = DEFAULT_CONTACT_POLICY) -> bool:
    hour = local_time.hour
    if config.quiet_hours_start_hour > config.quiet_hours_end_hour:
        # Window wraps midnight (e.g. 22:00 -> 08:00).
        return hour >= config.quiet_hours_start_hour or hour < config.quiet_hours_end_hour
    return config.quiet_hours_start_hour <= hour < config.quiet_hours_end_hour


def allocate_outreach(
    ranked_candidates: list[NBACandidate],
    now_local: datetime,
    opted_out: bool,
    attempts_today: int,
    attempts_this_week: int,
    config: ContactPolicyConfig = DEFAULT_CONTACT_POLICY,
) -> list[OutreachDecision]:
    """Draws from all of a customer's lines' eligible actions in priority
    order until the shared cap is reached (FR-014). Suppressed decisions do
    not consume a cap slot (data-model.md §OutreachAttempt)."""
    if opted_out:
        return [OutreachDecision(c, "SUPPRESSED", "OPTED_OUT") for c in ranked_candidates]

    if is_quiet_hours(now_local, config):
        return [OutreachDecision(c, "SUPPRESSED", "QUIET_HOURS") for c in ranked_candidates]

    remaining_daily = max(0, config.max_per_day - attempts_today)
    remaining_weekly = max(0, config.max_per_week - attempts_this_week)

    decisions: list[OutreachDecision] = []
    for candidate in ranked_candidates:
        if remaining_weekly <= 0:
            decisions.append(OutreachDecision(candidate, "SUPPRESSED", "WEEKLY_CAP"))
            continue
        if remaining_daily <= 0:
            decisions.append(OutreachDecision(candidate, "SUPPRESSED", "DAILY_CAP"))
            continue
        decisions.append(OutreachDecision(candidate, "DELIVERED", None))
        remaining_daily -= 1
        remaining_weekly -= 1

    return decisions
