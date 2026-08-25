from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_db, issue_session_token

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    customer_id: str


class LoginResponse(BaseModel):
    access_token: str
    customer_id: str


@router.post("/login", response_model=LoginResponse)
def login(body: LoginRequest, db: Session = Depends(get_db)) -> LoginResponse:
    account_exists = _customer_has_account(db, body.customer_id)
    if not account_exists:
        raise HTTPException(status_code=404, detail="Unknown seeded customer_id")
    token = issue_session_token(body.customer_id)
    return LoginResponse(access_token=token, customer_id=body.customer_id)


def _customer_has_account(db: Session, customer_id: str) -> bool:
    from concierge.persistence.models import Account

    return db.query(Account).filter_by(customer_id=customer_id).first() is not None
