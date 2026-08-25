from concierge.analytics.dashboard import DashboardMetrics, EngagementCounts
from concierge.analytics.pocr_porr import estimate_pocr_porr


def _metrics(digital_resolutions=0):
    return DashboardMetrics(
        enrolled_customers=5,
        engagement=EngagementCounts(proactive_contacts_delivered=3, chat_sessions=2),
        onboarding_completion_rate=0.5,
        digital_resolutions=digital_resolutions,
        escalations=1,
    )


def test_estimate_always_simulated_true():
    estimate = estimate_pocr_porr(_metrics(digital_resolutions=10))
    assert estimate.simulated is True


def test_estimate_always_has_a_non_empty_label():
    estimate = estimate_pocr_porr(_metrics())
    assert isinstance(estimate.label, str)
    assert len(estimate.label) > 0
    assert "simulated" in estimate.label.lower() or "projected" in estimate.label.lower()


def test_estimate_with_zero_resolutions_is_zero_not_negative():
    estimate = estimate_pocr_porr(_metrics(digital_resolutions=0))
    assert estimate.potential_pocr_interventions == 0
    assert estimate.potential_porr_interventions == 0


def test_estimate_scales_with_digital_resolutions():
    low = estimate_pocr_porr(_metrics(digital_resolutions=2))
    high = estimate_pocr_porr(_metrics(digital_resolutions=20))
    assert high.potential_pocr_interventions > low.potential_pocr_interventions
    assert high.potential_porr_interventions > low.potential_porr_interventions


def test_porr_is_never_larger_than_pocr():
    """The prepaid/postpaid ratio design assumption (research/analytics):
    retail-visit avoidance is a smaller subset of call avoidance."""
    estimate = estimate_pocr_porr(_metrics(digital_resolutions=15))
    assert estimate.potential_porr_interventions <= estimate.potential_pocr_interventions
