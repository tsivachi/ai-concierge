from datetime import date

from pydantic import BaseModel


class PostpaidEstimateOut(BaseModel):
    recurring_charges: float
    one_time_charges: float
    device_installment: float
    taxes_fees: float
    promotional_credits: float
    total_estimate: float
    cycle_start: date
    cycle_end: date
    estimate_note: str


class PrepaidRenewalOut(BaseModel):
    balance: float
    renewal_date: date
    data_allowance: str
    auto_recharge_enabled: bool
    expiration_date: date | None
    renewal_ready: bool


class BillingOrRenewalViewOut(BaseModel):
    plan_type: str
    postpaid_estimate: PostpaidEstimateOut | None = None
    prepaid_renewal: PrepaidRenewalOut | None = None
    explanation: str
