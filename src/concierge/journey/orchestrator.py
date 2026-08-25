"""JourneyOrchestrator: the application coordinator that routes an ingested
event to the correct ActivityInstance transition(s) and writes an auditable
StateTransitionLog entry for every change (FR-009; Constitution Principle VI).

Health-score/NBA recomputation hooks (Phase 5) attach here once they exist;
this module stays free of any AI/LLM call (Constitution Principle I).
"""

from datetime import datetime

from sqlalchemy.orm import Session

from concierge.domain.enums import ActivityScope
from concierge.journey.activity_catalog import scope_for_activity_code
from concierge.journey.transitions import activity_codes_for_event, next_status_for_event
from concierge.persistence.repositories import JourneyRepository


def apply_event_to_journey(
    session: Session,
    journey_id: str,
    line_id: str | None,
    event_id: str,
    event_type: str,
    occurred_at: datetime,
    correlation_id: str | None,
) -> list[str]:
    """Applies event_type's effects to every matching ActivityInstance for
    this journey/line. Returns the list of instance_ids that changed."""
    journey_repo = JourneyRepository(session)
    changed: list[str] = []

    for activity_code in activity_codes_for_event(event_type):
        scope = scope_for_activity_code(activity_code)
        target_line_id = line_id if scope == ActivityScope.LINE else None

        if scope == ActivityScope.LINE and target_line_id is None:
            continue  # a line-scoped activity needs a line_id to resolve which line

        instance = journey_repo.get_activity_instance(journey_id, target_line_id, activity_code)
        if instance is None:
            continue  # not instantiated for this journey/line (e.g. wrong plan type)

        new_status = next_status_for_event(activity_code, instance.status, event_type)
        if new_status is None or new_status == instance.status:
            continue

        before_state = {"status": instance.status}
        instance.status = new_status
        instance.last_applied_event_occurred_at = occurred_at
        session.flush()
        after_state = {"status": new_status}

        journey_repo.log_state_transition(
            journey_id=journey_id,
            line_id=target_line_id,
            entity_type="ACTIVITY_INSTANCE",
            entity_id=instance.instance_id,
            before_state=before_state,
            after_state=after_state,
            triggering_event_id=event_id,
            correlation_id=correlation_id,
        )
        changed.append(instance.instance_id)

    return changed
