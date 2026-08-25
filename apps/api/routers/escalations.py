from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from apps.api.deps import get_current_customer, get_db
from apps.api.journey_access import require_journey_owner
from apps.api.schemas.escalations import REASON_VALUES, EscalationCaseOut, EscalationCreateIn
from concierge.conversation.context import activity_snapshots_from_context, assemble_context
from concierge.decisioning import escalation as escalation_module
from concierge.persistence.repositories import DecisionRepository

router = APIRouter(prefix="/api/escalations", tags=["escalations"])


def _to_out(case) -> EscalationCaseOut:
    return EscalationCaseOut(
        case_id=case.case_id,
        journey_id=case.journey_id,
        line_id=case.line_id,
        reason=case.reason,
        priority=case.priority,
        journey_snapshot=case.journey_snapshot,
        relevant_event_ids=case.relevant_event_ids,
        attempted_action_ids=case.attempted_action_ids,
        conversation_summary=case.conversation_summary,
        status=case.status,
        created_at=case.created_at,
    )


@router.post("", response_model=EscalationCaseOut, status_code=201)
def post_escalation(
    body: EscalationCreateIn,
    db: Session = Depends(get_db),
    customer_id: str | None = Depends(get_current_customer),
) -> EscalationCaseOut:
    require_journey_owner(db, body.journey_id, customer_id)

    if body.reason not in REASON_VALUES:
        raise HTTPException(status_code=422, detail=f"Unknown escalation reason: {body.reason}")

    if body.line_id is None:
        raise HTTPException(status_code=422, detail="line_id is required to assemble escalation context")

    context = assemble_context(db, body.journey_id, body.line_id)
    case = escalation_module.create_escalation_case(
        db,
        journey_id=body.journey_id,
        line_id=body.line_id,
        reason=body.reason,
        activities=activity_snapshots_from_context(context),
        conversation_summary="Explicit escalation requested via POST /api/escalations",
        health={"score": context.health.score, "band": context.health.band} if context.health else None,
        nba={"action_code": context.current_nba.action_code} if context.current_nba else None,
    )
    return _to_out(case)


@router.get("", response_model=EscalationCaseOut)
def get_escalation(
    case_id: str,
    db: Session = Depends(get_db),
    customer_id: str | None = Depends(get_current_customer),
) -> EscalationCaseOut:
    if customer_id is None:
        raise HTTPException(status_code=401, detail="Authenticated context required")

    decision_repo = DecisionRepository(db)
    case = decision_repo.get_escalation_case(case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="No such escalation case")

    require_journey_owner(db, case.journey_id, customer_id)
    return _to_out(case)
