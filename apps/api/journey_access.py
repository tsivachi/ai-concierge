"""Shared ownership-check helper for every customer-specific journey route
(FR-021; closes analyze finding C2 / checklist CHK015): 401 if unauthenticated,
403 if the authenticated customer does not own the journey, 404 if it
doesn't exist at all."""

from fastapi import HTTPException
from sqlalchemy.orm import Session

from concierge.persistence.models import AccountJourney
from concierge.persistence.repositories import JourneyRepository


def require_journey_owner(db: Session, journey_id: str, customer_id: str | None) -> AccountJourney:
    if customer_id is None:
        raise HTTPException(status_code=401, detail="Authenticated context required")

    journey_repo = JourneyRepository(db)
    journey = journey_repo.get_journey(journey_id)
    if journey is None:
        raise HTTPException(status_code=404, detail="No such journey")

    account = journey_repo.get_account(journey.account_id)
    if account is None or account.customer_id != customer_id:
        raise HTTPException(status_code=403, detail="Not authorized for this journey")

    return journey
