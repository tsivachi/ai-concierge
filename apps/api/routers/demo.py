from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from apps.api.deps import get_db
from concierge.journey.scenario_loader import ScenarioNotFoundError, list_scenarios, load_scenario

router = APIRouter(prefix="/api/demo", tags=["demo"])


class DemoScenarioSummary(BaseModel):
    scenario_id: str
    title: str
    description: str


class ScenarioResetResponse(BaseModel):
    scenario_id: str
    title: str
    account_id: str
    customer_id: str
    journey_id: str
    line_ids: list[str]
    events_applied: int


@router.get("/scenarios", response_model=list[DemoScenarioSummary])
def get_scenarios() -> list[DemoScenarioSummary]:
    return [DemoScenarioSummary(**s) for s in list_scenarios()]


@router.post("/scenarios/{scenario_id}/reset", response_model=ScenarioResetResponse)
def reset_scenario(scenario_id: str, db: Session = Depends(get_db)) -> ScenarioResetResponse:
    try:
        result = load_scenario(db, scenario_id)
    except ScenarioNotFoundError:
        raise HTTPException(status_code=404, detail=f"Unknown scenario: {scenario_id}") from None
    return ScenarioResetResponse(**result)
