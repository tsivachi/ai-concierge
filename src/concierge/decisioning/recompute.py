"""I/O-touching coordination layer: loads state, calls the pure decisioning
functions (health_score, nba, friction, contact_policy), and persists the
results — including a StateTransitionLog entry for every HealthScoreRecord
and NextBestActionRecord change (FR-009; closes analyze finding H3).

This is the "downstream health/NBA recomputation hook" JourneyOrchestrator
calls after applying an event's activity transitions.
"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from concierge.decisioning.contact_policy import allocate_outreach
from concierge.decisioning.friction import compute_friction_for_line
from concierge.decisioning.health_score import compute_account_health_score, compute_line_health_score
from concierge.decisioning.models import ActivitySnapshot
from concierge.decisioning.nba import current_nba_for_line, rank_candidates
from concierge.persistence.decision_models import ConsentPreference, OutreachAttempt
from concierge.persistence.repositories import ConsentRepository, DecisionRepository, JourneyRepository


def _load_activity_snapshots(journey_repo: JourneyRepository, journey_id: str, line_id: str) -> list[ActivitySnapshot]:
    instances = journey_repo.list_activity_instances_for_journey(journey_id)
    return [
        ActivitySnapshot(activity_code=i.activity_code, requirement_class=i.requirement_class, status=i.status)
        for i in instances
        if i.line_id in (line_id, None)
    ]


def recompute_line(
    session: Session, journey_id: str, line_id: str, journey_started_at: datetime, as_of: datetime | None = None
):
    as_of = as_of or datetime.now(timezone.utc)
    journey_day = (as_of - journey_started_at.replace(tzinfo=timezone.utc)).days

    journey_repo = JourneyRepository(session)
    decision_repo = DecisionRepository(session)

    activities = _load_activity_snapshots(journey_repo, journey_id, line_id)
    friction = compute_friction_for_line(session, journey_id, line_id, as_of)
    health = compute_line_health_score(activities, friction)

    before_health = decision_repo.get_current_health_score(journey_id, line_id)
    health_record = decision_repo.save_health_score(
        journey_id=journey_id, line_id=line_id, score=health.score, band=health.band, reason_codes=health.reason_codes
    )
    journey_repo.log_state_transition(
        journey_id=journey_id,
        line_id=line_id,
        entity_type="HEALTH_SCORE",
        entity_id=health_record.id,
        before_state={"score": before_health.score, "band": before_health.band} if before_health else None,
        after_state={"score": health.score, "band": health.band},
    )

    open_escalations = decision_repo.list_open_escalations_for_line(line_id)
    suppressed = frozenset(
        e.related_action_code for e in open_escalations if e.related_action_code is not None
    )
    nba = current_nba_for_line(activities, journey_day, suppressed_action_codes=suppressed)

    nba_record = None
    if nba is not None:
        decision_repo.supersede_current_nba(line_id, as_of)
        nba_record = decision_repo.save_next_best_action(
            journey_id=journey_id,
            line_id=line_id,
            action_code=nba.action_code,
            priority=nba.priority,
            tie_break_rank=nba.tie_break_rank,
            reason_codes=nba.reason_codes,
        )
        journey_repo.log_state_transition(
            journey_id=journey_id,
            line_id=line_id,
            entity_type="NEXT_BEST_ACTION",
            entity_id=nba_record.id,
            after_state={"action_code": nba.action_code, "priority": nba.priority},
        )

    return health_record, nba_record


def recompute_account(session: Session, journey_id: str, line_ids: list[str], as_of: datetime | None = None):
    as_of = as_of or datetime.now(timezone.utc)
    decision_repo = DecisionRepository(session)
    journey_repo = JourneyRepository(session)

    line_scores = []
    for line_id in line_ids:
        record = decision_repo.get_current_health_score(journey_id, line_id)
        if record is not None:
            line_scores.append(record.score)

    score, band = compute_account_health_score(line_scores)
    before = decision_repo.get_current_health_score(journey_id, None)
    record = decision_repo.save_health_score(journey_id=journey_id, line_id=None, score=score, band=band, reason_codes=[])
    journey_repo.log_state_transition(
        journey_id=journey_id,
        line_id=None,
        entity_type="HEALTH_SCORE",
        entity_id=record.id,
        before_state={"score": before.score, "band": before.band} if before else None,
        after_state={"score": score, "band": band},
    )
    return record


def recompute_journey(session: Session, journey_id: str, line_ids: list[str], journey_started_at: datetime, as_of: datetime | None = None):
    """Recomputes health + NBA for every line, then the account aggregate."""
    as_of = as_of or datetime.now(timezone.utc)
    for line_id in line_ids:
        recompute_line(session, journey_id, line_id, journey_started_at, as_of)
    return recompute_account(session, journey_id, line_ids, as_of)


def allocate_outreach_for_journey(
    session: Session, customer_id: str, journey_id: str, line_ids: list[str], as_of: datetime | None = None
):
    """Cross-line outreach allocation (FR-014, Clarifications Q2): ranks every
    line's current NBA together and draws from that single ranked list until
    the shared per-customer contact cap is reached."""
    as_of = as_of or datetime.now(timezone.utc)
    decision_repo = DecisionRepository(session)
    consent_repo = ConsentRepository(session)

    candidates = []
    nba_record_id_by_line: dict[str, str] = {}
    for line_id in line_ids:
        record = decision_repo.get_current_nba_for_line(line_id)
        if record is not None:
            from concierge.decisioning.models import NBACandidate

            candidates.append(
                NBACandidate(
                    line_id=line_id,
                    action_code=record.action_code,
                    priority=record.priority,
                    tie_break_rank=record.tie_break_rank,
                    reason_codes=record.reason_codes,
                )
            )
            nba_record_id_by_line[line_id] = record.id

    ranked = rank_candidates(candidates)

    consent = consent_repo.get_consent(customer_id)
    opted_out = consent.opted_out if consent is not None else False

    day_start = as_of.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = day_start.replace(day=max(1, day_start.day - day_start.weekday()))
    attempts_today = (
        session.query(OutreachAttempt)
        .filter(
            OutreachAttempt.customer_id == customer_id,
            OutreachAttempt.status == "DELIVERED",
            OutreachAttempt.attempted_at >= day_start,
        )
        .count()
    )
    attempts_this_week = (
        session.query(OutreachAttempt)
        .filter(
            OutreachAttempt.customer_id == customer_id,
            OutreachAttempt.status == "DELIVERED",
            OutreachAttempt.attempted_at >= week_start,
        )
        .count()
    )

    decisions = allocate_outreach(ranked, as_of, opted_out, attempts_today, attempts_this_week)

    saved = []
    for decision in decisions:
        record = decision_repo.save_outreach_attempt(
            customer_id=customer_id,
            line_id=decision.candidate.line_id,
            next_best_action_id=nba_record_id_by_line[decision.candidate.line_id],
            channel="push",
            status=decision.status,
            suppression_reason=decision.suppression_reason,
        )
        saved.append(record)

    return saved
