from pydantic import BaseModel


class KnowledgeSearchResultOut(BaseModel):
    doc_id: str
    title: str
    topic: str
    snippet: str
    score: float
