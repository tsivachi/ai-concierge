"""FR-025: deterministic postpaid bill-estimate arithmetic against known
BillingSnapshot fixtures — the LLM never computes this, only explains it."""

from datetime import date

from concierge.decisioning.billing import compute_postpaid_bill_estimate


def _snapshot(**overrides):
    base = {
        "recurring_charges": 65.0,
        "one_time_charges": 35.0,
        "device_installment": 25.0,
        "taxes_fees": 8.5,
        "promotional_credits": -10.0,
        "cycle_start": date(2026, 8, 1),
        "cycle_end": date(2026, 8, 31),
    }
    base.update(overrides)
    return base


def test_total_estimate_sums_all_components():
    estimate = compute_postpaid_bill_estimate(_snapshot())
    assert estimate.total_estimate == 123.5


def test_promotional_credits_reduce_the_total():
    with_credit = compute_postpaid_bill_estimate(_snapshot(promotional_credits=-20.0))
    without_credit = compute_postpaid_bill_estimate(_snapshot(promotional_credits=0.0))
    assert with_credit.total_estimate == without_credit.total_estimate - 20.0


def test_total_is_rounded_to_two_decimal_places():
    estimate = compute_postpaid_bill_estimate(_snapshot(taxes_fees=8.333333))
    assert estimate.total_estimate == round(65.0 + 35.0 + 25.0 + 8.333333 - 10.0, 2)


def test_estimate_note_distinguishes_from_final_bill():
    estimate = compute_postpaid_bill_estimate(_snapshot())
    assert "estimate" in estimate.estimate_note.lower()
    assert "not" in estimate.estimate_note.lower()


def test_cycle_dates_pass_through_unchanged():
    estimate = compute_postpaid_bill_estimate(_snapshot())
    assert estimate.cycle_start == date(2026, 8, 1)
    assert estimate.cycle_end == date(2026, 8, 31)


def test_zero_charges_yields_zero_total():
    zero_snapshot = _snapshot(
        recurring_charges=0.0, one_time_charges=0.0, device_installment=0.0, taxes_fees=0.0, promotional_credits=0.0
    )
    estimate = compute_postpaid_bill_estimate(zero_snapshot)
    assert estimate.total_estimate == 0.0
