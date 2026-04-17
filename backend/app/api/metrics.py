"""
Patient-scoped Metrics API — Layer 2.

GET  /api/v1/patients/{patient_id}/daily-metrics
     Returns all computed DailyMetric rows for the patient, optionally
     filtered by from_date / to_date.  Ordered oldest → newest.

GET  /api/v1/patients/{patient_id}/latest-metrics
     Returns the single most recent DailyMetric row.
     404 if no metrics have been computed yet.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.daily_metric import DailyMetric
from app.models.patient import Patient
from app.schemas import DailyMetricRead

router = APIRouter()


def _get_patient_or_404(patient_id: int, db: Session) -> Patient:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return patient


@router.get("/{patient_id}/daily-metrics", response_model=list[DailyMetricRead])
def get_daily_metrics(
    patient_id: int,
    from_date: date | None = Query(
        default=None,
        description="Inclusive start date. Omit to return all available rows.",
    ),
    to_date: date | None = Query(
        default=None,
        description="Inclusive end date. Omit to return all available rows.",
    ),
    db: Session = Depends(get_db),
):
    """
    Return computed DailyMetric rows for the patient ordered oldest → newest.

    Both date filters are optional; omitting both returns the full history.
    Returns an empty list when no metrics have been computed yet — call
    POST /api/v1/compute-metrics first to populate the table.
    """
    _get_patient_or_404(patient_id, db)

    q = db.query(DailyMetric).filter(DailyMetric.patient_id == patient_id)

    if from_date is not None:
        q = q.filter(DailyMetric.metric_date >= from_date)
    if to_date is not None:
        q = q.filter(DailyMetric.metric_date <= to_date)

    return q.order_by(DailyMetric.metric_date.asc()).all()


@router.get("/{patient_id}/latest-metrics", response_model=DailyMetricRead)
def get_latest_metrics(
    patient_id: int,
    db: Session = Depends(get_db),
):
    """
    Return the most recent DailyMetric row for the patient.
    404 when no metrics have been computed yet.
    """
    _get_patient_or_404(patient_id, db)

    row = (
        db.query(DailyMetric)
        .filter(DailyMetric.patient_id == patient_id)
        .order_by(DailyMetric.metric_date.desc())
        .first()
    )
    if row is None:
        raise HTTPException(
            status_code=404,
            detail=f"No computed metrics found for patient {patient_id}. "
                   "Run POST /api/v1/compute-metrics to generate them.",
        )
    return row
