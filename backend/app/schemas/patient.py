from datetime import datetime
from pydantic import BaseModel, Field


class PatientCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=120)
    age: int = Field(..., ge=0, le=120)
    gender: str | None = None
    home_lat: float | None = None
    home_lng: float | None = None
    safe_radius_m: float = Field(200.0, gt=0)


class PatientUpdate(BaseModel):
    """All fields optional — send only what changed."""
    name: str | None = Field(None, min_length=1, max_length=120)
    age: int | None = Field(None, ge=0, le=120)
    gender: str | None = None
    home_lat: float | None = None
    home_lng: float | None = None
    safe_radius_m: float | None = Field(None, gt=0)


class PatientRead(BaseModel):
    id: int
    name: str
    age: int
    gender: str | None
    home_lat: float | None
    home_lng: float | None
    safe_radius_m: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
