"""Deterministic postpaid bill-estimate and prepaid renewal-readiness
computation (FR-025, FR-026). Pure functions over provider-supplied
snapshot dicts — the AI/LLM layer only ever explains these already-computed
figures (conversation/personalize.py), never calculates them
(Constitution Principle I).
"""

from dataclasses import dataclass
from datetime import date

ESTIMATE_NOTE = "This is an estimate based on charges on file for your account — not your final bill."


@dataclass(frozen=True)
class PostpaidBillEstimate:
    recurring_charges: float
    one_time_charges: float
    device_installment: float
    taxes_fees: float
    promotional_credits: float
    total_estimate: float
    cycle_start: date
    cycle_end: date
    estimate_note: str


@dataclass(frozen=True)
class RenewalReadiness:
    balance: float
    renewal_date: date
    data_allowance: str
    auto_recharge_enabled: bool
    expiration_date: date | None
    renewal_ready: bool


def compute_postpaid_bill_estimate(snapshot: dict) -> PostpaidBillEstimate:
    """Sums the provider-supplied figures into a plain-language total,
    explicitly labeled as an estimate rather than a final bill (FR-025)."""
    total = round(
        snapshot["recurring_charges"]
        + snapshot["one_time_charges"]
        + snapshot["device_installment"]
        + snapshot["taxes_fees"]
        + snapshot["promotional_credits"],
        2,
    )
    return PostpaidBillEstimate(
        recurring_charges=snapshot["recurring_charges"],
        one_time_charges=snapshot["one_time_charges"],
        device_installment=snapshot["device_installment"],
        taxes_fees=snapshot["taxes_fees"],
        promotional_credits=snapshot["promotional_credits"],
        total_estimate=total,
        cycle_start=snapshot["cycle_start"],
        cycle_end=snapshot["cycle_end"],
        estimate_note=ESTIMATE_NOTE,
    )


def compute_renewal_readiness(snapshot: dict) -> RenewalReadiness:
    """A prepaid line is 'renewal ready' when auto-recharge is enabled
    (renewal happens automatically) — the deterministic rule the
    prepaid-renewal knowledge article describes (FR-026)."""
    return RenewalReadiness(
        balance=snapshot["balance"],
        renewal_date=snapshot["renewal_date"],
        data_allowance=snapshot["data_allowance"],
        auto_recharge_enabled=snapshot["auto_recharge_enabled"],
        expiration_date=snapshot.get("expiration_date"),
        renewal_ready=bool(snapshot["auto_recharge_enabled"]),
    )
