import uuid
from datetime import datetime, timezone

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from concierge.domain.enums import ActivityStatus, JourneyStatus, LineJourneyStatus, PlanType, RequirementClass
from concierge.persistence.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Account(Base):
    __tablename__ = "accounts"

    account_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    customer_id: Mapped[str] = mapped_column(String, index=True)
    created_at: Mapped[datetime] = mapped_column(default=_utcnow)

    lines: Mapped[list["Line"]] = relationship(back_populates="account")
    journeys: Mapped[list["AccountJourney"]] = relationship(back_populates="account")


class Line(Base):
    __tablename__ = "lines"

    line_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"), index=True)
    plan_type: Mapped[PlanType] = mapped_column(SAEnum(PlanType))
    msisdn: Mapped[str | None] = mapped_column(String, nullable=True)
    device_info: Mapped[str | None] = mapped_column(String, nullable=True)

    account: Mapped["Account"] = relationship(back_populates="lines")


class AccountJourney(Base):
    """One 30-day account-level journey (spec.md FR-001; Constitution Principle III).

    At most one ACTIVE journey per account is an application-level invariant
    (spec.md Assumptions) enforced in enrollment logic (Phase 4, T042), not a
    DB constraint, to stay portable between SQLite and PostgreSQL.
    """

    __tablename__ = "account_journeys"
    __table_args__ = (Index("ix_account_journeys_account_status", "account_id", "status"),)

    journey_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    account_id: Mapped[str] = mapped_column(ForeignKey("accounts.account_id"))
    status: Mapped[JourneyStatus] = mapped_column(SAEnum(JourneyStatus), default=JourneyStatus.ACTIVE)
    started_at: Mapped[datetime] = mapped_column()
    expires_at: Mapped[datetime] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    account: Mapped["Account"] = relationship(back_populates="journeys")
    lines: Mapped[list["LineOnboardingState"]] = relationship(back_populates="journey")
    activity_instances: Mapped[list["ActivityInstance"]] = relationship(back_populates="journey")


class LineOnboardingState(Base):
    __tablename__ = "line_onboarding_states"

    line_id: Mapped[str] = mapped_column(ForeignKey("lines.line_id"), primary_key=True)
    journey_id: Mapped[str] = mapped_column(ForeignKey("account_journeys.journey_id"), index=True)
    plan_type: Mapped[PlanType] = mapped_column(SAEnum(PlanType))
    status: Mapped[LineJourneyStatus] = mapped_column(SAEnum(LineJourneyStatus), default=LineJourneyStatus.IN_PROGRESS)

    journey: Mapped["AccountJourney"] = relationship(back_populates="lines")
    activity_instances: Mapped[list["ActivityInstance"]] = relationship(back_populates="line")


class ActivityInstance(Base):
    """The tracked state of one ActivityDefinition for one account or line
    within a specific journey (data-model.md §ActivityInstance)."""

    __tablename__ = "activity_instances"
    __table_args__ = (
        Index("ix_activity_instances_journey_line_code", "journey_id", "line_id", "activity_code"),
    )

    instance_id: Mapped[str] = mapped_column(String, primary_key=True, default=_uuid)
    journey_id: Mapped[str] = mapped_column(ForeignKey("account_journeys.journey_id"))
    line_id: Mapped[str | None] = mapped_column(ForeignKey("line_onboarding_states.line_id"), nullable=True)
    activity_code: Mapped[str] = mapped_column(String)
    requirement_class: Mapped[RequirementClass] = mapped_column(SAEnum(RequirementClass))
    status: Mapped[ActivityStatus] = mapped_column(SAEnum(ActivityStatus), default=ActivityStatus.NOT_STARTED)
    updated_at: Mapped[datetime] = mapped_column(default=_utcnow, onupdate=_utcnow)
    last_applied_event_occurred_at: Mapped[datetime | None] = mapped_column(nullable=True)
    """Used by the out-of-order/terminal-state guard (FR events T033):
    an incoming event whose occurred_at precedes this value cannot regress a
    terminal status."""

    journey: Mapped["AccountJourney"] = relationship(back_populates="activity_instances")
    line: Mapped["LineOnboardingState | None"] = relationship(back_populates="activity_instances")
