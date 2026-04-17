from datetime import datetime
from pydantic import BaseModel


class WearSessionCreate(BaseModel):
    patient_id: int
    start_time: datetime


class WearSessionRead(BaseModel):
    id: int
    patient_id: int
    start_time: datetime
    end_time: datetime | None
    duration_minutes: float | None

    model_config = {"from_attributes": True}
