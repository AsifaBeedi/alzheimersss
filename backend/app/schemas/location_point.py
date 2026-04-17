from datetime import datetime
from pydantic import BaseModel, Field


class LocationPointCreate(BaseModel):
    patient_id: int
    timestamp: datetime
    lat: float = Field(..., ge=-90, le=90)
    lng: float = Field(..., ge=-180, le=180)
    speed_mps: float | None = Field(None, ge=0)
    heading_deg: float | None = Field(None, ge=0, lt=360)


class LocationPointRead(BaseModel):
    id: int
    patient_id: int
    timestamp: datetime
    lat: float
    lng: float
    speed_mps: float | None
    heading_deg: float | None

    model_config = {"from_attributes": True}
