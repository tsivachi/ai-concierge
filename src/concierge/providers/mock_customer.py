"""Deterministic seeded mock for CustomerProvider (FR-029). Reads from the
already-seeded Account table rather than re-parsing scenario files, so it
always reflects whatever scenario is currently loaded."""

from sqlalchemy.orm import Session

from concierge.persistence.models import Account


class MockCustomerProvider:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_customer(self, customer_id: str) -> dict | None:
        account = self._session.query(Account).filter_by(customer_id=customer_id).first()
        if account is None:
            return None
        return {"customer_id": account.customer_id, "account_id": account.account_id}
