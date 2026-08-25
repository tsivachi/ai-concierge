"""Deterministic seeded mock for BillingProvider (FR-029). Reads whatever
BillingSnapshot/RenewalSnapshot rows the active demo scenario seeded —
returns None when a line has no billing/renewal fixture (e.g. a scenario
that doesn't exercise billing)."""

from sqlalchemy.orm import Session

from concierge.persistence.repositories import BillingRepository


class MockBillingProvider:
    def __init__(self, session: Session) -> None:
        self._repo = BillingRepository(session)

    def get_billing_snapshot(self, line_id: str) -> dict | None:
        record = self._repo.get_latest_billing_snapshot(line_id)
        if record is None:
            return None
        return {
            "recurring_charges": record.recurring_charges,
            "one_time_charges": record.one_time_charges,
            "device_installment": record.device_installment,
            "taxes_fees": record.taxes_fees,
            "promotional_credits": record.promotional_credits,
            "cycle_start": record.cycle_start,
            "cycle_end": record.cycle_end,
        }

    def get_renewal_snapshot(self, line_id: str) -> dict | None:
        record = self._repo.get_latest_renewal_snapshot(line_id)
        if record is None:
            return None
        return {
            "balance": record.balance,
            "renewal_date": record.renewal_date,
            "data_allowance": record.data_allowance,
            "auto_recharge_enabled": record.auto_recharge_enabled,
            "expiration_date": record.expiration_date,
            "add_ons": record.add_ons,
        }
