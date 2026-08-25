from datetime import datetime

from pydantic import BaseModel


class ReasonCodeOut(BaseModel):
    code: str
    label: str
    deduction: int | None = None


class NextBestActionOut(BaseModel):
    line_id: str
    action_code: str
    priority: int
    tie_break_rank: int
    reason_codes: list[ReasonCodeOut]
    message: str | None = None
    computed_at: datetime


class HealthScoreOut(BaseModel):
    scope: str  # ACCOUNT | LINE
    line_id: str | None = None
    score: int
    band: str
    reason_codes: list[ReasonCodeOut]


class HealthScoreView(BaseModel):
    account: HealthScoreOut
    lines: list[HealthScoreOut]
