from contextlib import asynccontextmanager

from fastapi import FastAPI

from apps.api.middleware import CorrelationIdMiddleware, configure_logging
from apps.api.routers import auth, chat, dashboard, demo, escalations, events, journeys, knowledge
from concierge.knowledge.ingest import ingest_knowledge_base
from concierge.persistence.db import get_session_factory, init_db

configure_logging()


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    session = get_session_factory()()
    try:
        ingest_knowledge_base(session)
        session.commit()
    finally:
        session.close()
    yield


app = FastAPI(title="30-Day Personalized AI Concierge", lifespan=lifespan)
app.add_middleware(CorrelationIdMiddleware)

app.include_router(events.router)
app.include_router(demo.router)
app.include_router(auth.router)
app.include_router(journeys.router)
app.include_router(knowledge.router)
app.include_router(chat.router)
app.include_router(escalations.router)
app.include_router(dashboard.router)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}
