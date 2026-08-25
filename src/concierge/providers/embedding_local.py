"""Local, non-network EmbeddingProvider (FR-029) backed by Chroma's bundled
ONNX MiniLM model (research.md §3) — no hosted embeddings API key required
for the demo's core RAG path to work."""

from chromadb.utils import embedding_functions


class LocalEmbeddingProvider:
    def __init__(self) -> None:
        self._fn = embedding_functions.DefaultEmbeddingFunction()

    def embed(self, texts: list[str]) -> list[list[float]]:
        return [list(vec) for vec in self._fn(texts)]

    def chroma_embedding_function(self):
        """Exposes the underlying Chroma-native callable directly, so
        knowledge/ingest.py and retrieval.py can hand it straight to a
        Chroma collection without re-wrapping."""
        return self._fn
