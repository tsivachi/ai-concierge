from datetime import datetime

from pydantic import BaseModel


class ActivityInstanceOut(BaseModel):
    activity_code: str
    status: str
    requirement_class: str


class LineOnboardingStateOut(BaseModel):
    line_id: str
    plan_type: str
    status: str
    activities: list[ActivityInstanceOut]


class AccountJourneyViewOut(BaseModel):
    journey_id: str
    account_id: str
    status: str
    started_at: datetime
    expires_at: datetime
    current_day: int
    account_activities: list[ActivityInstanceOut]
    lines: list[LineOnboardingStateOut]
