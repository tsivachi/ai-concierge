"""Grounded-answer orchestration (FR-020..FR-024, FR-027). The LLM only ever
personalizes/explains an answer already assembled from real, deterministic
sources — it never decides whether a request is in-scope, never sees
anything outside ConciergeContext + retrieved KnowledgeDocuments, never
executes an action, and never decides whether to escalate. Constitution
Principle I: every eligibility/whitelisting/escalation decision here is
plain Python, not the LLM.
"""

from dataclasses import dataclass, field

from sqlalchemy.orm import Session

from concierge.conversation import attempts
from concierge.conversation.context import ConciergeContext, activity_snapshots_from_context, assemble_context
from concierge.decisioning import escalation as escalation_module
from concierge.decisioning.nba import BASE_PRIORITY
from concierge.knowledge.retrieval import RetrievedDocument, search_knowledge
from concierge.persistence.repositories import DecisionRepository

# Deterministic account-specific detector (Constitution Principle I): the
# *decision* to decline an unauthenticated request must not be delegated to
# the LLM, so this is a plain keyword heuristic, not a model call.
ACCOUNT_SPECIFIC_MARKERS = (
    "my account",
    "my line",
    "my bill",
    "my balance",
    "my order",
    "my activation",
    "my number",
    "my plan",
    "is my",
    "my journey",
    "my next step",
)

# FR-024 / spec.md Assumptions (CHK028): the supported action set is the
# next-best-action catalog already enumerated in FR-011/nba.py.
SUPPORTED_ACTION_CODES = frozenset(BASE_PRIORITY.keys())

UNSUPPORTED_ACTION_PHRASES = (
    "cancel my line",
    "cancel my account",
    "cancel this line",
    "refund",
    "change my plan",
    "downgrade my plan",
    "upgrade my plan",
    "delete my account",
    "delete my line",
)

_RELEVANT_EVENT_TYPES_BY_REASON = {
    "UNRESOLVED_ACTIVATION_OR_PORT": (
        "DeviceActivationStarted",
        "DeviceActivationFailed",
        "NumberTransferRequested",
        "NumberTransferPending",
        "NumberTransferFailed",
    ),
    "SENSITIVE_ACCOUNT_SECURITY": ("CustomerLoggedIn", "SupportCaseCreated"),
    "BILLING_DISPUTE": ("SupportCaseCreated",),
    "EXPLICIT_REQUEST": ("ChatStarted", "SupportCaseCreated"),
    "TWO_FAILED_TROUBLESHOOTING": ("ChatStarted", "HelpArticleViewed"),
    "UNSUPPORTED_LOW_CONFIDENCE": ("ChatStarted",),
}

ESCALATION_ANSWER_TEXT = (
    "I've connected this to a human agent who can help further — they'll have your full "
    "journey history and won't need you to repeat anything."
)


@dataclass(frozen=True)
class ChatAnswer:
    answer: str
    sources: list[dict] = field(default_factory=list)
    authenticated: bool = False
    declined: bool = False
    unsupported_action_requested: bool = False
    escalated: bool = False
    escalation_case_id: str | None = None


def looks_account_specific(question: str) -> bool:
    q = question.lower()
    return any(marker in q for marker in ACCOUNT_SPECIFIC_MARKERS)


def requests_unsupported_action(question: str) -> bool:
    q = question.lower()
    return any(phrase in q for phrase in UNSUPPORTED_ACTION_PHRASES)


def _sources_payload(retrieved: list[RetrievedDocument]) -> list[dict]:
    return [{"doc_id": r.doc_id, "title": r.title, "topic": r.topic} for r in retrieved]


def answer_unauthenticated(question: str, llm_provider) -> ChatAnswer:
    """FR-020/FR-021: generic questions answered from knowledge retrieval
    only; account-specific questions declined with an authenticate prompt.
    Zero customer-specific data ever enters this code path — escalation
    (which requires a journey_id) is out of scope here by construction."""
    if looks_account_specific(question):
        return ChatAnswer(
            answer="I can't share account-specific details without you signing in first. Please authenticate and ask again.",
            declined=True,
            authenticated=False,
        )

    retrieved = search_knowledge(question)
    context = {"kind": "chat_answer", "sources": _sources_payload(retrieved), "current_nba_label": None}
    answer_text = llm_provider.generate(question, context)
    return ChatAnswer(answer=answer_text, sources=context["sources"], authenticated=False)


def _determine_escalation_reason(
    session: Session, session_id: str, question: str, context: ConciergeContext, retrieved: list[RetrievedDocument]
) -> tuple[str | None, str | None]:
    """Checks all 6 FR-027 triggers in priority order (escalation.REASON_PRIORITY)
    and returns (reason, related_action_code), or (None, None) if none fire."""
    activity_snapshots = activity_snapshots_from_context(context)

    related_action_code = escalation_module.unresolved_activation_or_port_trigger(activity_snapshots)
    if related_action_code is not None:
        return "UNRESOLVED_ACTIVATION_OR_PORT", related_action_code

    if escalation_module.sensitive_security_trigger(question):
        return "SENSITIVE_ACCOUNT_SECURITY", None

    if escalation_module.billing_dispute_trigger(question):
        return "BILLING_DISPUTE", None

    if escalation_module.explicit_request_trigger(question):
        return "EXPLICIT_REQUEST", None

    if escalation_module.unsupported_low_confidence_trigger(len(retrieved), requests_unsupported_action(question)):
        return "UNSUPPORTED_LOW_CONFIDENCE", None

    if retrieved:
        topic = retrieved[0].topic
        prior_unresolved = attempts.count_consecutive_unresolved_attempts(session, session_id, topic)
        if escalation_module.two_failed_troubleshooting_trigger(prior_unresolved + 1):
            return "TWO_FAILED_TROUBLESHOOTING", None

    return None, None


def _escalate(
    session: Session,
    journey_id: str,
    line_id: str,
    reason: str,
    related_action_code: str | None,
    question: str,
    context: ConciergeContext,
    retrieved: list[RetrievedDocument],
) -> str:
    """Idempotent: reuses an already-open case for the same issue rather
    than creating a duplicate (FR-028a's suppression only works if there's
    exactly one open case per issue)."""
    decision_repo = DecisionRepository(session)
    existing = (
        decision_repo.get_open_escalation_for_action(line_id, related_action_code)
        if related_action_code
        else None
    )
    if existing is not None:
        return existing.case_id

    case = escalation_module.create_escalation_case(
        session,
        journey_id=journey_id,
        line_id=line_id,
        reason=reason,
        activities=activity_snapshots_from_context(context),
        related_action_code=related_action_code,
        relevant_event_types=_RELEVANT_EVENT_TYPES_BY_REASON.get(reason, ()),
        attempted_action_ids=[context.current_nba.action_code] if context.current_nba else [],
        conversation_summary=f"Customer asked: \"{question}\"",
        health={"score": context.health.score, "band": context.health.band} if context.health else None,
        nba={"action_code": context.current_nba.action_code} if context.current_nba else None,
    )
    return case.case_id


def answer_authenticated(
    session: Session, question: str, journey_id: str, line_id: str, session_id: str, llm_provider
) -> ChatAnswer:
    """FR-022/FR-023/FR-024/FR-027: grounded in the customer's real state
    plus retrieved knowledge; the LLM never invents facts, mutates state,
    claims to have performed an unsupported action, or decides to escalate."""
    context: ConciergeContext = assemble_context(session, journey_id, line_id)
    retrieved = search_knowledge(question)
    unsupported = requests_unsupported_action(question)

    reason, related_action_code = _determine_escalation_reason(session, session_id, question, context, retrieved)

    if reason is not None:
        case_id = _escalate(session, journey_id, line_id, reason, related_action_code, question, context, retrieved)
        return ChatAnswer(
            answer=ESCALATION_ANSWER_TEXT,
            sources=_sources_payload(retrieved),
            authenticated=True,
            unsupported_action_requested=unsupported,
            escalated=True,
            escalation_case_id=case_id,
        )

    current_nba_label = context.current_nba.action_code if context.current_nba else None
    llm_context = {
        "kind": "chat_answer",
        "sources": _sources_payload(retrieved),
        "current_nba_label": current_nba_label,
    }
    answer_text = llm_provider.generate(question, llm_context)
    return ChatAnswer(answer=answer_text, sources=llm_context["sources"], authenticated=True)
