from pydantic import BaseModel


class EngagementOut(BaseModel):
    proactive_contacts_delivered: int
    chat_sessions: int


class DashboardViewOut(BaseModel):
    simulated: bool
    enrolled_customers: int
    engagement: EngagementOut
    onboarding_completion_rate: float
    digital_resolutions: int
    escalations: int
    potential_pocr_interventions: int
    potential_porr_interventions: int
    label: str
