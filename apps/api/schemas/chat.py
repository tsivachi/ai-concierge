from pydantic import BaseModel


class ChatRequestIn(BaseModel):
    session_id: str
    message: str


class KnowledgeSourceRefOut(BaseModel):
    doc_id: str
    title: str
    topic: str


class ChatResponseOut(BaseModel):
    session_id: str
    authenticated: bool
    answer: str
    sources: list[KnowledgeSourceRefOut]
    escalated: bool = False
    escalation_case_id: str | None = None
