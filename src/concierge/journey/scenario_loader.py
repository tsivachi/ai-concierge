"""Loads a seeds/scenarios/*.json file into the database, truncating any prior
scenario state first (FR-032, SC-011). Backdates AccountJourney.started_at and
every seeded event's occurred_at per research.md §6, so day-3/5/7/10/21
thresholds are already true on load — no real-time waiting required.
"""

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from concierge.domain.enums import PlanType
from concierge.events.ingestion import IngestResult, ingest_event
from concierge.journey.enrollment import instantiate_activities_for_line
from concierge.persistence.repositories import (
    BillingRepository,
    ConsentRepository,
    DecisionRepository,
    EventRepository,
    JourneyRepository,
)

SCENARIOS_DIR = Path(__file__).resolve().parents[3] / "seeds" / "scenarios"

JOURNEY_LENGTH_DAYS = 30


class ScenarioNotFoundError(Exception):
    pass


def list_scenarios() -> list[dict]:
    scenarios = []
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        data = json.loads(path.read_text())
        scenarios.append(
            {
                "scenario_id": data["scenario_id"],
                "title": data["title"],
                "description": data.get("description", ""),
            }
        )
    return scenarios


def load_scenario(session: Session, scenario_id: str) -> dict:
    path = SCENARIOS_DIR / f"{scenario_id}.json"
    if not path.exists():
        raise ScenarioNotFoundError(scenario_id)
    data = json.loads(path.read_text())

    journey_repo = JourneyRepository(session)
    event_repo = EventRepository(session)
    decision_repo = DecisionRepository(session)
    consent_repo = ConsentRepository(session)
    billing_repo = BillingRepository(session)

    # Reset: clear all prior scenario state so no residue leaks between loads (SC-011).
    decision_repo.truncate_all()
    event_repo.truncate_all()
    consent_repo.truncate_all()
    billing_repo.truncate_all()
    journey_repo.truncate_all()
    session.flush()

    now = datetime.now(timezone.utc)
    started_at = now - timedelta(days=data["journey_started_at_offset_days"])
    expires_at = started_at + timedelta(days=JOURNEY_LENGTH_DAYS)

    account = data["account"]
    journey_repo.create_account(account["account_id"], account["customer_id"])
    journey = journey_repo.create_journey(account["account_id"], started_at, expires_at)

    for line in data["lines"]:
        plan_type = PlanType(line["plan_type"])
        journey_repo.create_line(line["line_id"], account["account_id"], plan_type.value)
        journey_repo.create_line_onboarding_state(line["line_id"], journey.journey_id, plan_type.value)
        instantiate_activities_for_line(
            journey_repo, journey.journey_id, line["line_id"], plan_type, line.get("number_port_requested", False)
        )

    for customer_id, prefs in data.get("consent", {}).items():
        consent_repo.set_opted_out(customer_id, prefs.get("opted_out", False))

    billing_snapshot = data.get("billing_snapshot")
    if billing_snapshot is not None:
        billing_repo.save_billing_snapshot(
            line_id=billing_snapshot["line_id"],
            recurring_charges=billing_snapshot["recurring_charges"],
            one_time_charges=billing_snapshot["one_time_charges"],
            device_installment=billing_snapshot["device_installment"],
            taxes_fees=billing_snapshot["taxes_fees"],
            promotional_credits=billing_snapshot["promotional_credits"],
            cycle_start=(now - timedelta(days=billing_snapshot["cycle_start_offset_days"])).date(),
            cycle_end=(now - timedelta(days=billing_snapshot["cycle_end_offset_days"])).date(),
        )

    renewal_snapshot = data.get("renewal_snapshot")
    if renewal_snapshot is not None:
        expiration_offset = renewal_snapshot.get("expiration_date_offset_days")
        billing_repo.save_renewal_snapshot(
            line_id=renewal_snapshot["line_id"],
            balance=renewal_snapshot["balance"],
            renewal_date=(now - timedelta(days=renewal_snapshot["renewal_date_offset_days"])).date(),
            data_allowance=renewal_snapshot["data_allowance"],
            auto_recharge_enabled=renewal_snapshot["auto_recharge_enabled"],
            expiration_date=(now - timedelta(days=expiration_offset)).date() if expiration_offset is not None else None,
            add_ons=renewal_snapshot.get("add_ons", []),
        )

    session.flush()

    results: list[IngestResult] = []
    for event in data.get("events", []):
        occurred_at = now - timedelta(days=event["occurred_at_offset_days"])
        payload = {**event, "occurred_at": occurred_at.isoformat()}
        payload.pop("occurred_at_offset_days", None)
        results.append(ingest_event(session, payload))

    session.flush()

    # Guarantee a baseline health/NBA exists even for scenarios whose seed
    # events don't touch an ActivityInstance (e.g. OrderCompleted only).
    from concierge.decisioning.recompute import recompute_journey

    line_ids = [line["line_id"] for line in data["lines"]]
    recompute_journey(session, journey.journey_id, line_ids, started_at, as_of=now)
    session.flush()

    return {
        "scenario_id": data["scenario_id"],
        "title": data["title"],
        "account_id": account["account_id"],
        "customer_id": account["customer_id"],
        "journey_id": journey.journey_id,
        "line_ids": [line["line_id"] for line in data["lines"]],
        "events_applied": len(results),
    }
