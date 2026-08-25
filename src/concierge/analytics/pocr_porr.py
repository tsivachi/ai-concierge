"""Simulated POCR/PORR intervention-count estimation (FR-035; Constitution
Principle X). A deliberately simple, transparent formula over already-computed
digital-resolution and escalation counts — always paired with a `simulated`
flag and a disclaimer label, and never presented as measured causal
reduction."""

from dataclasses import dataclass

from concierge.analytics.dashboard import DashboardMetrics

SIMULATED_LABEL = (
    "Simulated/projected hackathon metric — not a measured reduction in real call or retail volume."
)

# Illustrative, documented ratios (not derived from any real measurement):
# every digital resolution is assumed to represent one avoided support call;
# retail visits are assumed rarer, so only a fraction of resolutions map to one.
POCR_RATIO = 1.0
PORR_RATIO = 0.3


@dataclass(frozen=True)
class PocrPorrEstimate:
    potential_pocr_interventions: int
    potential_porr_interventions: int
    simulated: bool
    label: str


def estimate_pocr_porr(metrics: DashboardMetrics) -> PocrPorrEstimate:
    potential_pocr = round(metrics.digital_resolutions * POCR_RATIO)
    potential_porr = round(metrics.digital_resolutions * PORR_RATIO)
    return PocrPorrEstimate(
        potential_pocr_interventions=potential_pocr,
        potential_porr_interventions=potential_porr,
        simulated=True,
        label=SIMULATED_LABEL,
    )
