"""FR-026: prepaid renewal-readiness derivation."""

from datetime import date

from concierge.decisioning.billing import compute_renewal_readiness


def _snapshot(**overrides):
    base = {
        "balance": 12.5,
        "renewal_date": date(2026, 8, 28),
        "data_allowance": "5GB",
        "auto_recharge_enabled": False,
        "expiration_date": None,
        "add_ons": [],
    }
    base.update(overrides)
    return base


def test_renewal_ready_when_auto_recharge_enabled():
    readiness = compute_renewal_readiness(_snapshot(auto_recharge_enabled=True))
    assert readiness.renewal_ready is True


def test_renewal_not_ready_when_auto_recharge_disabled():
    readiness = compute_renewal_readiness(_snapshot(auto_recharge_enabled=False))
    assert readiness.renewal_ready is False


def test_fields_pass_through_unchanged():
    readiness = compute_renewal_readiness(_snapshot())
    assert readiness.balance == 12.5
    assert readiness.renewal_date == date(2026, 8, 28)
    assert readiness.data_allowance == "5GB"


def test_expiration_date_defaults_to_none_when_absent():
    snapshot = _snapshot()
    del snapshot["expiration_date"]
    readiness = compute_renewal_readiness(snapshot)
    assert readiness.expiration_date is None


def test_expiration_date_passes_through_when_present():
    readiness = compute_renewal_readiness(_snapshot(expiration_date=date(2026, 9, 15)))
    assert readiness.expiration_date == date(2026, 9, 15)
