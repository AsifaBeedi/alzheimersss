from datetime import datetime
from pydantic import BaseModel
from app.models.enums import AlertType, AlertStatus, Severity


class AlertRead(BaseModel):
    id: int
    patient_id: int
    alert_type: AlertType
    severity: Severity
    description: str
    timestamp: datetime
    status: AlertStatus
    metadata_json: dict | None

    model_config = {"from_attributes": True}
