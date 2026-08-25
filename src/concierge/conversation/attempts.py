"""Troubleshooting-attempt tracking (feeds FR-027's two-attempt escalation
trigger; consumed by Phase 9's escalation workflow). Persists each turn and
counts consecutive unresolved attempts on the same topic within a session."""

from sqlalchemy.orm import Session

from concierge.persistence.conversation_models import ConversationSession, ConversationTurn

TWO_ATTEMPT_ESCALATION_THRESHOLD = 2


def get_or_create_session(session: Session, session_id: str, customer_id: str | None) -> ConversationSession:
    existing = session.get(ConversationSession, session_id)
    if existing is not None:
        return existing
    record = ConversationSession(session_id=session_id, customer_id=customer_id)
    session.add(record)
    session.flush()
    return record


def record_turn(
    session: Session,
    session_id: str,
    role: str,
    text: str,
    retrieved_source_ids: list[str] | None = None,
    troubleshooting_topic: str | None = None,
    resolved: bool | None = None,
) -> ConversationTurn:
    turn = ConversationTurn(
        session_id=session_id,
        role=role,
        text=text,
        retrieved_source_ids=retrieved_source_ids or [],
        troubleshooting_topic=troubleshooting_topic,
        resolved=resolved,
    )
    session.add(turn)
    session.flush()
    return turn


def count_consecutive_unresolved_attempts(session: Session, session_id: str, topic: str) -> int:
    """Counts unresolved concierge turns on `topic`, most-recent-first, until
    a resolved turn or a different topic breaks the streak."""
    turns = (
        session.query(ConversationTurn)
        .filter_by(session_id=session_id, role="concierge")
        .order_by(ConversationTurn.created_at.desc())
        .all()
    )
    count = 0
    for turn in turns:
        if turn.troubleshooting_topic != topic:
            break
        if turn.resolved:
            break
        count += 1
    return count


def should_escalate_for_repeated_troubleshooting(session: Session, session_id: str, topic: str) -> bool:
    return count_consecutive_unresolved_attempts(session, session_id, topic) >= TWO_ATTEMPT_ESCALATION_THRESHOLD
