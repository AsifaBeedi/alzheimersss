"""
Patient Timeline API.

GET /api/v1/patients/{patient_id}/timeline

Returns all Event rows for a patient sorted chronologically (oldest → newest).
Each entry carries the event type, severity, GPS coordinates, and the
metadata_json payload so the frontend can render event-specific detail cards.

Optional filters:
  from_date / to_date  — narrow to a date range (both inclusive)
  limit                — cap results (default 500, max 2000)
"""

from datetime import date, datetime, time

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.event import Event
from app.models.patient import Patient
from app.schemas.event import EventRead

router = APIRouter()


def _get_patient_or_404(patient_id: int, db: Session) -> Patient:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return patient


@router.get("/{patient_id}/timeline", response_model=list[EventRead])
def get_timeline(
    patient_id: int,
    from_date: date | None = Query(
        default=None,
        description="Inclusive start date. Omit to include the full history.",
    ),
    to_date: date | None = Query(
        default=None,
        description="Inclusive end date. Omit to include events up to now.",
    ),
    limit: int = Query(
        default=500,
        ge=1,
        le=2000,
        description="Maximum number of events to return.",
    ),
    db: Session = Depends(get_db),
):
    """
    Return all clinical events for the patient in chronological order.

    Events are sorted oldest → newest so the frontend can render them as a
    scrollable timeline without reversing.

    Each event includes:
    - `event_type`    — WANDERING_EPISODE | WRONG_TURN | FALL | AGITATION
    - `severity`      — info | warning | critical
    - `timestamp`     — UTC datetime of the event
    - `lat` / `lng`   — GPS location at time of event (nullable)
    - `metadata_json` — event-specific payload (subtype, distances, context)
    """
    _get_patient_or_404(patient_id, db)

    q = db.query(Event).filter(Event.patient_id == patient_id)

    if from_date is not None:
        q = q.filter(Event.timestamp >= datetime.combine(from_date, time.min))
    if to_date is not None:
        q = q.filter(Event.timestamp <= datetime.combine(to_date, time.max))

    return q.order_by(Event.timestamp.asc()).limit(limit).all()
