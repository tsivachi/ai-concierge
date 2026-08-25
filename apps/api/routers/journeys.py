from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_current_customer, get_db
from apps.api.journey_access import require_journey_owner
from apps.api.llm_factory import get_llm_provider
from apps.api.schemas.billing import BillingOrRenewalViewOut, PostpaidEstimateOut, PrepaidRenewalOut
from apps.api.schemas.decisioning import HealthScoreOut, HealthScoreView, NextBestActionOut, ReasonCodeOut
from apps.api.schemas.journey import AccountJourneyViewOut, ActivityInstanceOut, LineOnboardingStateOut
from concierge.conversation.personalize import personalize_billing_explanation, personalize_nba_message
from concierge.decisioning.billing import compute_postpaid_bill_estimate, compute_renewal_readiness
from concierge.decisioning.recompute import recompute_journey
from concierge.journey.status import ActivityStatusView, derive_journey_status, is_line_complete
from concierge.persistence.repositories import JourneyRepository
from concierge.providers.mock_billing import MockBillingProvider

router = APIRouter(prefix="/api/journeys", tags=["journeys"])


@router.get("/{journey_id}", response_model=AccountJourneyViewOut)
def get_journey(
    journey_id: str,
    db: Session = Depends(get_db),
    customer_id: str | None = Depends(get_current_customer),
) -> AccountJourneyViewOut:
    journey = require_journey_owner(db, journey_id, customer_id)
    journey_repo = JourneyRepository(db)

    line_states = journey_repo.list_line_states_for_journey(journey_id)
    all_activities = journey_repo.list_activity_instances_for_journey(journey_id)
    account_activities = [a for a in all_activities if a.line_id is None]

    def _activity_out(a) -> ActivityInstanceOut:
        return ActivityInstanceOut(activity_code=a.activity_code, status=a.status, requirement_class=a.requirement_class)

    def _to_status_view(a) -> ActivityStatusView:
        return ActivityStatusView(activity_code=a.activity_code, status=a.status, requirement_class=a.requirement_class)

    account_activity_views = [_to_status_view(a) for a in account_activities]

    lines_out = []
    line_complete_flags = []
    for state in line_states:
        line_activities = [a for a in all_activities if a.line_id == state.line_id]
        line_activity_views = [_to_status_view(a) for a in line_activities]
        complete = is_line_complete(line_activity_views, account_activity_views)
        line_complete_flags.append(complete)
        lines_out.append(
            LineOnboardingStateOut(
                line_id=state.line_id,
                plan_type=state.plan_type,
                status="COMPLETE" if complete else "IN_PROGRESS",
                activities=[_activity_out(a) for a in line_activities],
            )
        )

    now = datetime.now(timezone.utc)
    started_at = journey.started_at if journey.started_at.tzinfo else journey.started_at.replace(tzinfo=timezone.utc)
    current_day = (now - started_at).days
    status = derive_journey_status(line_complete_flags, journey.expires_at, as_of=now)

    return AccountJourneyViewOut(
        journey_id=journey.journey_id,
        account_id=journey.account_id,
        status=status,
        started_at=journey.started_at,
        expires_at=journey.expires_at,
        current_day=current_day,
        account_activities=[_activity_out(a) for a in account_activities],
        lines=lines_out,
    )


@router.get("/{journey_id}/recommendation", response_model=list[NextBestActionOut])
def get_recommendation(
    journey_id: str,
    db: Session = Depends(get_db),
    customer_id: str | None = Depends(get_current_customer),
) -> list[NextBestActionOut]:
    journey = require_journey_owner(db, journey_id, customer_id)
    journey_repo = JourneyRepository(db)
    line_ids = [s.line_id for s in journey_repo.list_line_states_for_journey(journey_id)]

    recompute_journey(db, journey_id, line_ids, journey.started_at, as_of=datetime.now(timezone.utc))

    from concierge.persistence.repositories import DecisionRepository

    decision_repo = DecisionRepository(db)
    llm_provider = get_llm_provider()
    results = []
    for line_id in line_ids:
        record = decision_repo.get_current_nba_for_line(line_id)
        if record is None:
            continue
        if record.message is None:
            # Personalization is additive-only: it only ever fills in the
            # wording for an already-finalized, already-persisted NBA — the
            # priority/reason_codes above are untouched (T101a, FR-013).
            record.message = personalize_nba_message(llm_provider, record.action_code)
            db.flush()
        results.append(
            NextBestActionOut(
                line_id=line_id,
                action_code=record.action_code,
                priority=record.priority,
                tie_break_rank=record.tie_break_rank,
                reason_codes=[ReasonCodeOut(**rc) for rc in record.reason_codes],
                message=record.message,
                computed_at=record.computed_at,
            )
        )
    return results


@router.get("/{journey_id}/health", response_model=HealthScoreView)
def get_health(
    journey_id: str,
    db: Session = Depends(get_db),
    customer_id: str | None = Depends(get_current_customer),
) -> HealthScoreView:
    journey = require_journey_owner(db, journey_id, customer_id)
    journey_repo = JourneyRepository(db)
    line_ids = [s.line_id for s in journey_repo.list_line_states_for_journey(journey_id)]

    account_record = recompute_journey(db, journey_id, line_ids, journey.started_at, as_of=datetime.now(timezone.utc))

    from concierge.persistence.repositories import DecisionRepository

    decision_repo = DecisionRepository(db)
    line_scores = []
    for line_id in line_ids:
        record = decision_repo.get_current_health_score(journey_id, line_id)
        if record is None:
            continue
        line_scores.append(
            HealthScoreOut(
                scope="LINE",
                line_id=line_id,
                score=record.score,
                band=record.band,
                reason_codes=[ReasonCodeOut(**rc) for rc in record.reason_codes],
            )
        )

    return HealthScoreView(
        account=HealthScoreOut(
            scope="ACCOUNT", line_id=None, score=account_record.score, band=account_record.band, reason_codes=[]
        ),
        lines=line_scores,
    )


@router.get("/{journey_id}/billing", response_model=BillingOrRenewalViewOut)
def get_billing(
    journey_id: str,
    line_id: str,
    db: Session = Depends(get_db),
    customer_id: str | None = Depends(get_current_customer),
) -> BillingOrRenewalViewOut:
    """FR-025/FR-026: postpaid bill estimate or prepaid renewal readiness,
    computed deterministically from provider-supplied facts (decisioning/billing.py);
    the LLM only explains the already-computed figures (T101b)."""
    require_journey_owner(db, journey_id, customer_id)
    journey_repo = JourneyRepository(db)

    line_state = journey_repo.get_line_onboarding_state(line_id)
    if line_state is None or line_state.journey_id != journey_id:
        raise HTTPException(status_code=404, detail="No such line on this journey")

    billing_provider = MockBillingProvider(db)
    llm_provider = get_llm_provider()

    postpaid_estimate_out = None
    prepaid_renewal_out = None

    if line_state.plan_type == "POSTPAID":
        snapshot = billing_provider.get_billing_snapshot(line_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="No billing data available for this line yet")
        estimate = compute_postpaid_bill_estimate(snapshot)
        postpaid_estimate_out = PostpaidEstimateOut(**estimate.__dict__)
        explanation = personalize_billing_explanation(llm_provider, postpaid_estimate_out.model_dump(mode="json"), None)
    else:
        snapshot = billing_provider.get_renewal_snapshot(line_id)
        if snapshot is None:
            raise HTTPException(status_code=404, detail="No renewal data available for this line yet")
        readiness = compute_renewal_readiness(snapshot)
        prepaid_renewal_out = PrepaidRenewalOut(**readiness.__dict__)
        explanation = personalize_billing_explanation(llm_provider, None, prepaid_renewal_out.model_dump(mode="json"))

    return BillingOrRenewalViewOut(
        plan_type=line_state.plan_type,
        postpaid_estimate=postpaid_estimate_out,
        prepaid_renewal=prepaid_renewal_out,
        explanation=explanation,
    )
