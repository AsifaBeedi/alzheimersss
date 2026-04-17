from datetime import date
from pydantic import BaseModel
from app.models.clinical_summary import SummaryPeriod


class ClinicalSummaryRead(BaseModel):
    id: int
    patient_id: int
    period: SummaryPeriod
    period_start: date
    period_end: date

    mobility_score: float | None = None
    safety_score: float | None = None
    adherence_score: float | None = None
    orientation_score: float | None = None
    composite_independence_score: float | None = None

    change_alerts: list[str] = []
    metric_snapshot: dict = {}

    model_config = {"from_attributes": True}
