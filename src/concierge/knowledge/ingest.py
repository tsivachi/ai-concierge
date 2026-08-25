"""Parses knowledge_base/*.md into KnowledgeDocument rows and upserts them
into a local Chroma collection. Idempotent: re-running produces the same
state (topic is used as the stable id on both sides), so it's safe to call
on every app startup (T086)."""

import os
from pathlib import Path

import chromadb
from sqlalchemy.orm import Session

from concierge.persistence.conversation_models import KnowledgeDocument
from concierge.providers.embedding_local import LocalEmbeddingProvider

KNOWLEDGE_BASE_DIR = Path(__file__).resolve().parents[3] / "knowledge_base"
COLLECTION_NAME = "knowledge_documents"

_client: chromadb.ClientAPI | None = None


def _chroma_persist_dir() -> str:
    return os.environ.get("CHROMA_PERSIST_DIR", "./chroma_data")


def get_chroma_client() -> chromadb.ClientAPI:
    global _client
    if _client is None:
        _client = chromadb.PersistentClient(path=_chroma_persist_dir())
    return _client


def reset_chroma_client_for_tests() -> None:
    global _client
    _client = None


def _parse_markdown(path: Path) -> tuple[str, str]:
    """Returns (title, body) — title is the first H1 line, body is everything
    after it."""
    text = path.read_text()
    lines = text.splitlines()
    title = path.stem.replace("-", " ").title()
    body_start = 0
    for i, line in enumerate(lines):
        if line.startswith("# "):
            title = line[2:].strip()
            body_start = i + 1
            break
    body = "\n".join(lines[body_start:]).strip()
    return title, body


def ingest_knowledge_base(session: Session) -> list[str]:
    """Returns the list of topics ingested."""
    embedding_provider = LocalEmbeddingProvider()
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        COLLECTION_NAME, embedding_function=embedding_provider.chroma_embedding_function()
    )

    topics: list[str] = []
    ids, documents, metadatas = [], [], []

    for path in sorted(KNOWLEDGE_BASE_DIR.glob("*.md")):
        topic = path.stem
        title, body = _parse_markdown(path)
        topics.append(topic)

        ids.append(topic)
        documents.append(body)
        metadatas.append({"title": title, "topic": topic})

        existing = session.get(KnowledgeDocument, topic)
        if existing is None:
            session.add(KnowledgeDocument(doc_id=topic, topic=topic, title=title, body=body, chroma_embedding_id=topic))
        else:
            existing.title = title
            existing.body = body
            existing.chroma_embedding_id = topic

    if ids:
        collection.upsert(ids=ids, documents=documents, metadatas=metadatas)

    session.flush()
    return topics
