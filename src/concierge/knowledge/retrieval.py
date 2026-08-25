"""Queries the Chroma collection and returns ranked matches with source
metadata (doc_id/title/topic) — "RAG returns source metadata" (T087)."""

from dataclasses import dataclass

from concierge.knowledge.ingest import COLLECTION_NAME, get_chroma_client
from concierge.providers.embedding_local import LocalEmbeddingProvider


@dataclass(frozen=True)
class RetrievedDocument:
    doc_id: str
    title: str
    topic: str
    snippet: str
    score: float


def search_knowledge(query: str, top_k: int = 3) -> list[RetrievedDocument]:
    embedding_provider = LocalEmbeddingProvider()
    client = get_chroma_client()
    collection = client.get_or_create_collection(
        COLLECTION_NAME, embedding_function=embedding_provider.chroma_embedding_function()
    )

    if collection.count() == 0:
        return []

    result = collection.query(query_texts=[query], n_results=min(top_k, collection.count()))

    ids = result["ids"][0]
    documents = result["documents"][0]
    metadatas = result["metadatas"][0]
    distances = result["distances"][0]

    retrieved = []
    for doc_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
        # Chroma's default distance is smaller-is-better; expose it as a
        # 0-1 similarity score instead, which is friendlier for API consumers.
        score = max(0.0, 1.0 - distance)
        retrieved.append(
            RetrievedDocument(
                doc_id=doc_id,
                title=metadata.get("title", doc_id),
                topic=metadata.get("topic", doc_id),
                snippet=document[:280],
                score=round(score, 4),
            )
        )
    return retrieved
