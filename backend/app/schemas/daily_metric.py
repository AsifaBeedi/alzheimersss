from datetime import date
from pydantic import BaseModel


class DailyMetricRead(BaseModel):
    id: int
    patient_id: int
    metric_date: date

    wandering_episode_count: int | None
    wrong_turn_count: int | None
    movement_radius_m: float | None
    wear_hours: float | None
    fall_count: int | None
    independence_score: float | None

    model_config = {"from_attributes": True}
