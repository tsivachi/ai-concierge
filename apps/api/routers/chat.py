from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.deps import get_current_customer, get_db
from apps.api.llm_factory import get_llm_provider
from apps.api.schemas.chat import ChatRequestIn, ChatResponseOut
from concierge.conversation import attempts, engine
from concierge.persistence.repositories import JourneyRepository

router = APIRouter(prefix="/api", tags=["chat"])


@router.post("/chat", response_model=ChatResponseOut)
def post_chat(
    body: ChatRequestIn,
    db: Session = Depends(get_db),
    customer_id: str | None = Depends(get_current_customer),
) -> ChatResponseOut:
    attempts.get_or_create_session(db, body.session_id, customer_id)
    attempts.record_turn(db, body.session_id, role="user", text=body.message)

    llm_provider = get_llm_provider()

    if customer_id is None:
        result = engine.answer_unauthenticated(body.message, llm_provider)
    else:
        result = _answer_for_authenticated_customer(db, customer_id, body.message, body.session_id, llm_provider)

    top_topic = result.sources[0]["topic"] if result.sources else None
    # Escalating or declining resets the troubleshooting-attempt streak (the
    # loop that would otherwise re-trigger escalation is now broken); an
    # ordinary grounded answer defaults to unresolved so a second question on
    # the same topic can still reach the two-attempt threshold (FR-027).
    resolved = result.escalated or result.declined
    attempts.record_turn(
        db,
        body.session_id,
        role="concierge",
        text=result.answer,
        retrieved_source_ids=[s["doc_id"] for s in result.sources],
        troubleshooting_topic=top_topic,
        resolved=resolved,
    )

    return ChatResponseOut(
        session_id=body.session_id,
        authenticated=result.authenticated,
        answer=result.answer,
        sources=result.sources,
        escalated=result.escalated,
        escalation_case_id=result.escalation_case_id,
    )


def _answer_for_authenticated_customer(db: Session, customer_id: str, message: str, session_id: str, llm_provider):
    journey_repo = JourneyRepository(db)
    from concierge.persistence.models import Account

    account = db.query(Account).filter_by(customer_id=customer_id).first()
    if account is None:
        return engine.ChatAnswer(
            answer="I couldn't find an account for you. Please contact support.", authenticated=True, declined=True
        )

    journey = journey_repo.get_active_journey_for_account(account.account_id)
    if journey is None:
        return engine.ChatAnswer(
            answer="You don't have an active onboarding journey right now.", authenticated=True, declined=True
        )

    line_states = journey_repo.list_line_states_for_journey(journey.journey_id)
    if not line_states:
        return engine.ChatAnswer(answer="No lines found on your journey.", authenticated=True, declined=True)

    # Single-line assumption for this MVP slice (most demo scenarios have one
    # line); a multi-line concierge UI would let the customer pick a line.
    line_id = line_states[0].line_id

    return engine.answer_authenticated(db, message, journey.journey_id, line_id, session_id, llm_provider)
