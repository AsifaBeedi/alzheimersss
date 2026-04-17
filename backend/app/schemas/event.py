from datetime import datetime
from pydantic import BaseModel, Field
from app.models.enums import EventType, Severity


class EventCreate(BaseModel):
    patient_id: int
    event_type: EventType
    timestamp: datetime
    severity: Severity = Severity.INFO
    lat: float | None = Field(None, ge=-90, le=90)
    lng: float | None = Field(None, ge=-180, le=180)
    metadata_json: dict = {}


class EventRead(BaseModel):
    id: int
    patient_id: int
    event_type: EventType
    timestamp: datetime
    severity: Severity
    lat: float | None
    lng: float | None
    metadata_json: dict | None

    model_config = {"from_attributes": True}
