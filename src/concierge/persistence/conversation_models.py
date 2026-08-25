import uuid
from datetime import datetime, timezone

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from concierge.persistence.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ConversationSession(Base):
    __tablename__ = "conversation_sessions"

    session_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    customer_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    started_at: Mapped[datetime] = mapped_column(default=_utcnow)


class ConversationTurn(Base):
    """Not itemized in spec.md §Key Entities; introduced by the plan
    (data-model.md) because User Story 4 AC5 and FR-027 require counting
    consecutive unresolved troubleshooting attempts on the same topic."""

    __tablename__ = "conversation_turns"

    turn_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String, index=True)
    role: Mapped[str] = mapped_column(String)  # user | concierge
    text: Mapped[str] = mapped_column(String)
    retrieved_source_ids: Mapped[list] = mapped_column(JSON, default=list)
    troubleshooting_topic: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved: Mapped[bool | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    doc_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    topic: Mapped[str] = mapped_column(String, index=True)
    title: Mapped[str] = mapped_column(String)
    body: Mapped[str] = mapped_column(String)
    chroma_embedding_id: Mapped[str | None] = mapped_column(String, nullable=True)
