from fastapi import APIRouter, Query

from apps.api.schemas.knowledge import KnowledgeSearchResultOut
from concierge.knowledge.retrieval import search_knowledge

router = APIRouter(prefix="/api/knowledge", tags=["knowledge"])


@router.get("/search", response_model=list[KnowledgeSearchResultOut])
def get_knowledge_search(q: str = Query(..., min_length=1)) -> list[KnowledgeSearchResultOut]:
    results = search_knowledge(q)
    return [KnowledgeSearchResultOut(**r.__dict__) for r in results]
