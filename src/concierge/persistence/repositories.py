"""Repository layer: every caller outside `persistence/` talks to these
domain-shaped methods, never to a raw SQLAlchemy `Session` (research.md §1)."""

from datetime import datetime

from sqlalchemy import delete
from sqlalchemy.orm import Session

from concierge.persistence.billing_models import BillingSnapshot, RenewalSnapshot
from concierge.persistence.decision_models import (
    ConsentPreference,
    EscalationCase,
    HealthScoreRecord,
    NextBestActionRecord,
    OutreachAttempt,
)
from concierge.persistence.event_models import DeadLetterEvent, DomainEvent, ProcessedEvent, StateTransitionLog
from concierge.persistence.models import Account, AccountJourney, ActivityInstance, Line, LineOnboardingState


class JourneyRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    # -- Account / Line -----------------------------------------------------

    def get_account(self, account_id: str) -> Account | None:
        return self._session.get(Account, account_id)

    def create_account(self, account_id: str, customer_id: str) -> Account:
        account = Account(account_id=account_id, customer_id=customer_id)
        self._session.add(account)
        self._session.flush()
        return account

    def get_or_create_account(self, account_id: str, customer_id: str) -> Account:
        account = self.get_account(account_id)
        if account is not None:
            return account
        return self.create_account(account_id, customer_id)

    def create_line(self, line_id: str, account_id: str, plan_type: str) -> Line:
        line = Line(line_id=line_id, account_id=account_id, plan_type=plan_type)
        self._session.add(line)
        self._session.flush()
        return line

    def get_line(self, line_id: str) -> Line | None:
        return self._session.get(Line, line_id)

    # -- AccountJourney -------------------------------------------------------

    def get_journey(self, journey_id: str) -> AccountJourney | None:
        return self._session.get(AccountJourney, journey_id)

    def get_active_journey_for_account(self, account_id: str) -> AccountJourney | None:
        return (
            self._session.query(AccountJourney)
            .filter_by(account_id=account_id, status="ACTIVE")
            .one_or_none()
        )

    def create_journey(
        self, account_id: str, started_at: datetime, expires_at: datetime, journey_id: str | None = None
    ) -> AccountJourney:
        kwargs = {"account_id": account_id, "started_at": started_at, "expires_at": expires_at}
        if journey_id is not None:
            kwargs["journey_id"] = journey_id
        journey = AccountJourney(**kwargs)
        self._session.add(journey)
        self._session.flush()
        return journey

    # -- LineOnboardingState --------------------------------------------------

    def create_line_onboarding_state(self, line_id: str, journey_id: str, plan_type: str) -> LineOnboardingState:
        state = LineOnboardingState(line_id=line_id, journey_id=journey_id, plan_type=plan_type)
        self._session.add(state)
        self._session.flush()
        return state

    def get_line_onboarding_state(self, line_id: str) -> LineOnboardingState | None:
        return self._session.get(LineOnboardingState, line_id)

    def list_line_states_for_journey(self, journey_id: str) -> list[LineOnboardingState]:
        return self._session.query(LineOnboardingState).filter_by(journey_id=journey_id).all()

    # -- ActivityInstance -----------------------------------------------------

    def create_activity_instance(
        self,
        journey_id: str,
        line_id: str | None,
        activity_code: str,
        requirement_class: str,
        status: str,
    ) -> ActivityInstance:
        instance = ActivityInstance(
            journey_id=journey_id,
            line_id=line_id,
            activity_code=activity_code,
            requirement_class=requirement_class,
            status=status,
        )
        self._session.add(instance)
        self._session.flush()
        return instance

    def get_activity_instance(
        self, journey_id: str, line_id: str | None, activity_code: str
    ) -> ActivityInstance | None:
        return (
            self._session.query(ActivityInstance)
            .filter_by(journey_id=journey_id, line_id=line_id, activity_code=activity_code)
            .one_or_none()
        )

    def list_activity_instances_for_line(self, line_id: str) -> list[ActivityInstance]:
        return self._session.query(ActivityInstance).filter_by(line_id=line_id).all()

    def list_activity_instances_for_journey(self, journey_id: str) -> list[ActivityInstance]:
        return self._session.query(ActivityInstance).filter_by(journey_id=journey_id).all()

    # -- Audit ------------------------------------------------------------------

    def log_state_transition(
        self,
        journey_id: str,
        entity_type: str,
        entity_id: str,
        after_state: dict,
        line_id: str | None = None,
        before_state: dict | None = None,
        triggering_event_id: str | None = None,
        correlation_id: str | None = None,
    ) -> StateTransitionLog:
        entry = StateTransitionLog(
            journey_id=journey_id,
            line_id=line_id,
            entity_type=entity_type,
            entity_id=entity_id,
            before_state=before_state,
            after_state=after_state,
            triggering_event_id=triggering_event_id,
            correlation_id=correlation_id,
        )
        self._session.add(entry)
        self._session.flush()
        return entry

    # -- Scenario reset -----------------------------------------------------

    def truncate_all(self) -> None:
        """Used by the scenario loader's reset semantics (FR-032)."""
        for model in (ActivityInstance, LineOnboardingState, AccountJourney, Line, Account, StateTransitionLog):
            self._session.execute(delete(model))


class EventRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def is_processed(self, event_id: str) -> bool:
        return self._session.get(ProcessedEvent, event_id) is not None

    def mark_processed(self, event_id: str) -> None:
        self._session.add(ProcessedEvent(event_id=event_id))
        self._session.flush()

    def save_domain_event(self, **fields) -> DomainEvent:
        event = DomainEvent(**fields)
        self._session.add(event)
        self._session.flush()
        return event

    def get_domain_event(self, event_id: str) -> DomainEvent | None:
        return self._session.get(DomainEvent, event_id)

    def save_dead_letter(
        self, event_id: str, event_type: str, account_id: str, line_id: str | None, reason: str, raw_payload: dict
    ) -> DeadLetterEvent:
        entry = DeadLetterEvent(
            event_id=event_id,
            event_type=event_type,
            account_id=account_id,
            line_id=line_id,
            reason=reason,
            raw_payload=raw_payload,
        )
        self._session.add(entry)
        self._session.flush()
        return entry

    def truncate_all(self) -> None:
        for model in (ProcessedEvent, DomainEvent, DeadLetterEvent):
            self._session.execute(delete(model))


class DecisionRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_next_best_action(self, **fields) -> NextBestActionRecord:
        record = NextBestActionRecord(**fields)
        self._session.add(record)
        self._session.flush()
        return record

    def get_current_nba_for_line(self, line_id: str) -> NextBestActionRecord | None:
        return (
            self._session.query(NextBestActionRecord)
            .filter_by(line_id=line_id, superseded_at=None)
            .order_by(NextBestActionRecord.computed_at.desc())
            .first()
        )

    def supersede_current_nba(self, line_id: str, superseded_at: datetime) -> None:
        current = self.get_current_nba_for_line(line_id)
        if current is not None:
            current.superseded_at = superseded_at
            self._session.flush()

    def save_health_score(self, **fields) -> HealthScoreRecord:
        record = HealthScoreRecord(**fields)
        self._session.add(record)
        self._session.flush()
        return record

    def get_current_health_score(self, journey_id: str, line_id: str | None) -> HealthScoreRecord | None:
        return (
            self._session.query(HealthScoreRecord)
            .filter_by(journey_id=journey_id, line_id=line_id)
            .order_by(HealthScoreRecord.computed_at.desc())
            .first()
        )

    def save_outreach_attempt(self, **fields) -> OutreachAttempt:
        record = OutreachAttempt(**fields)
        self._session.add(record)
        self._session.flush()
        return record

    def save_escalation_case(self, **fields) -> EscalationCase:
        case = EscalationCase(**fields)
        self._session.add(case)
        self._session.flush()
        return case

    def get_escalation_case(self, case_id: str) -> EscalationCase | None:
        return self._session.get(EscalationCase, case_id)

    def get_open_escalation_for_line(self, line_id: str) -> EscalationCase | None:
        return (
            self._session.query(EscalationCase)
            .filter_by(line_id=line_id, status="OPEN")
            .order_by(EscalationCase.created_at.desc())
            .first()
        )

    def list_open_escalations_for_line(self, line_id: str) -> list[EscalationCase]:
        return self._session.query(EscalationCase).filter_by(line_id=line_id, status="OPEN").all()

    def get_open_escalation_for_action(self, line_id: str, action_code: str) -> EscalationCase | None:
        return (
            self._session.query(EscalationCase)
            .filter_by(line_id=line_id, status="OPEN", related_action_code=action_code)
            .order_by(EscalationCase.created_at.desc())
            .first()
        )

    def truncate_all(self) -> None:
        for model in (NextBestActionRecord, HealthScoreRecord, OutreachAttempt, EscalationCase):
            self._session.execute(delete(model))


class ConsentRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def get_consent(self, customer_id: str) -> ConsentPreference | None:
        return self._session.get(ConsentPreference, customer_id)

    def set_opted_out(self, customer_id: str, opted_out: bool) -> ConsentPreference:
        pref = self.get_consent(customer_id)
        if pref is None:
            pref = ConsentPreference(customer_id=customer_id, opted_out=opted_out)
            self._session.add(pref)
        else:
            pref.opted_out = opted_out
        self._session.flush()
        return pref

    def truncate_all(self) -> None:
        self._session.execute(delete(ConsentPreference))


class BillingRepository:
    def __init__(self, session: Session) -> None:
        self._session = session

    def save_billing_snapshot(self, **fields) -> BillingSnapshot:
        record = BillingSnapshot(**fields)
        self._session.add(record)
        self._session.flush()
        return record

    def get_latest_billing_snapshot(self, line_id: str) -> BillingSnapshot | None:
        return (
            self._session.query(BillingSnapshot)
            .filter_by(line_id=line_id)
            .order_by(BillingSnapshot.fetched_at.desc())
            .first()
        )

    def save_renewal_snapshot(self, **fields) -> RenewalSnapshot:
        record = RenewalSnapshot(**fields)
        self._session.add(record)
        self._session.flush()
        return record

    def get_latest_renewal_snapshot(self, line_id: str) -> RenewalSnapshot | None:
        return (
            self._session.query(RenewalSnapshot)
            .filter_by(line_id=line_id)
            .order_by(RenewalSnapshot.fetched_at.desc())
            .first()
        )

    def truncate_all(self) -> None:
        for model in (BillingSnapshot, RenewalSnapshot):
            self._session.execute(delete(model))
