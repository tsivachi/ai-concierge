import uuid
from datetime import date, datetime, timezone

from sqlalchemy import JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from concierge.persistence.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BillingSnapshot(Base):
    """Provider-supplied postpaid billing facts (FR-025); the deterministic
    estimate shown to the customer is computed from these fields only."""

    __tablename__ = "billing_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    line_id: Mapped[str] = mapped_column(String, index=True)
    recurring_charges: Mapped[float] = mapped_column()
    one_time_charges: Mapped[float] = mapped_column()
    device_installment: Mapped[float] = mapped_column()
    taxes_fees: Mapped[float] = mapped_column()
    promotional_credits: Mapped[float] = mapped_column()
    cycle_start: Mapped[date] = mapped_column()
    cycle_end: Mapped[date] = mapped_column()
    fetched_at: Mapped[datetime] = mapped_column(default=_utcnow)


class RenewalSnapshot(Base):
    """Provider-supplied prepaid facts (FR-026)."""

    __tablename__ = "renewal_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    line_id: Mapped[str] = mapped_column(String, index=True)
    balance: Mapped[float] = mapped_column()
    renewal_date: Mapped[date] = mapped_column()
    data_allowance: Mapped[str] = mapped_column(String)
    auto_recharge_enabled: Mapped[bool] = mapped_column()
    expiration_date: Mapped[date | None] = mapped_column(nullable=True)
    add_ons: Mapped[list] = mapped_column(JSON, default=list)
    fetched_at: Mapped[datetime] = mapped_column(default=_utcnow)


class RiskScoreSnapshot(Base):
    """Mock/deterministic churn/call/retail/adoption scores (FR-031) —
    an unconsumed extensibility seam in this MVP, not wired into NBA/health."""

    __tablename__ = "risk_score_snapshots"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    account_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    line_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    churn_score: Mapped[float] = mapped_column()
    call_likelihood_score: Mapped[float] = mapped_column()
    retail_visit_likelihood_score: Mapped[float] = mapped_column()
    adoption_score: Mapped[float] = mapped_column()
    computed_at: Mapped[datetime] = mapped_column(default=_utcnow)
