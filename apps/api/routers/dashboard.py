from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from apps.api.schemas.dashboard import DashboardViewOut, EngagementOut
from concierge.analytics.dashboard import compute_dashboard_metrics
from concierge.analytics.pocr_porr import estimate_pocr_porr

router = APIRouter(prefix="/api", tags=["dashboard"])


@router.get("/dashboard", response_model=DashboardViewOut)
def get_dashboard(db: Session = Depends(get_db)) -> DashboardViewOut:
    metrics = compute_dashboard_metrics(db)
    estimate = estimate_pocr_porr(metrics)

    return DashboardViewOut(
        simulated=True,
        enrolled_customers=metrics.enrolled_customers,
        engagement=EngagementOut(**metrics.engagement.__dict__),
        onboarding_completion_rate=metrics.onboarding_completion_rate,
        digital_resolutions=metrics.digital_resolutions,
        escalations=metrics.escalations,
        potential_pocr_interventions=estimate.potential_pocr_interventions,
        potential_porr_interventions=estimate.potential_porr_interventions,
        label=estimate.label,
    )
