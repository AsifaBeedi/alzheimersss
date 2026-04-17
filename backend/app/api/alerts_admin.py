"""
Alerts Admin API — on-demand alert generation trigger.

POST /api/v1/generate-alerts
    Inspect all stored DailyMetric rows for every patient and create Alert
    rows for any threshold breaches not already recorded.

    Safe to call repeatedly — the deduplication key
    (patient_id, alert_type, rule_key, metric_date) prevents duplicate rows
    from being written on subsequent calls.

    Intended to be run after POST /api/v1/compute-metrics has populated the
    DailyMetric table.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.jobs.generate_alerts import generate_alerts_for_all_patients

router = APIRouter()


class GenerateAlertsResult(BaseModel):
    patients:        int   # distinct patient IDs processed
    dates_evaluated: int   # DailyMetric rows inspected across all patients
    alerts_created:  int   # new Alert rows written
    errors:          int   # patient/date pairs that raised an exception


@router.post("/", response_model=GenerateAlertsResult, status_code=200)
def generate_alerts(db: Session = Depends(get_db)):
    """
    Evaluate alert rules for all patients across all stored DailyMetric dates.

    Rules evaluated per patient-day:
    - **Fall detected** — fall_count > 0 on that day
    - **Increased wandering** — 7-day episode count meets or exceeds threshold
    - **Navigation confusion** — 7-day wrong-turn count meets or exceeds threshold
    - **Low wear adherence** — 7-day mean wear hours below threshold
    - **Movement radius decline** — week-over-week radius drop ≥ threshold %
    - **Low independence score** — composite score below threshold on that day

    Duplicate prevention: an alert is only written once per
    (patient, rule, date) combination — repeated calls are safe.

    Returns a summary of what was evaluated and written.
    """
    result = generate_alerts_for_all_patients(db)
    return GenerateAlertsResult(**result)
