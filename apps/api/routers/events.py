from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.events import EventAck, EventIn
from concierge.events.ingestion import ingest_event

router = APIRouter(prefix="/api", tags=["events"])


@router.post("/events", response_model=EventAck, status_code=202)
def post_event(event: EventIn, db: Session = Depends(get_db)) -> EventAck:
    payload = event.model_dump(mode="json")
    payload["event_type"] = event.event_type.value
    result = ingest_event(db, payload)
    return EventAck(event_id=result.event_id, outcome=result.outcome)
