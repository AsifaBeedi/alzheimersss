"""
Patient Summary API — Layer 3.

GET /api/v1/patients/{patient_id}/summary

Returns a single-shot response containing:
  - Latest value for each of the 6 Phase 1 metrics
  - All open alerts for the patient
  - 30-day trend series for each metric (oldest → newest, for sparklines)

Optional `as_of_date` query param lets callers request a historical snapshot.
Defaults to today.
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.patient import Patient
from app.schemas.alert import AlertRead
from app.services.summary_engine import build_patient_summary

router = APIRouter()


# ---------------------------------------------------------------------------
# Response schema
# ---------------------------------------------------------------------------

class TrendPoint(BaseModel):
    """One data point in a metric trend series."""
    metric_date: date
    value: float | None    # None = device not worn / data gap


class DataSourcesResponse(BaseModel):
    """
    Indicates where each metric group's data came from.
    Lets the frontend label metrics as pipeline-driven vs simulated.

    Possible values per field:
      "pipeline_jsonl"  — MITRA pipeline events imported via JSONL
      "synthetic"       — demo seed data (LocationPoints / WearSessions)
      "none"            — no source data; metric will be null
    """
    events:          str
    movement_radius: str
    wear_adherence:  str


class SummaryResponse(BaseModel):
    patient_id:  int
    as_of_date:  date
    window_days: int        # always 30 in current implementation

    # Latest (most recent non-null) values
    latest_independence_score:  float | None
    latest_wandering_count:     int   | None
    latest_wrong_turn_count:    int   | None
    latest_movement_radius_m:   float | None
    latest_wear_hours:          float | None
    latest_fall_count:          int   | None

    # All unresolved alerts, newest first
    open_alerts: list[AlertRead]

    # 30-day trend series for each metric, oldest → newest
    trend_independence_score:  list[TrendPoint]
    trend_wandering_count:     list[TrendPoint]
    trend_wrong_turn_count:    list[TrendPoint]
    trend_movement_radius_m:   list[TrendPoint]
    trend_wear_hours:          list[TrendPoint]
    trend_fall_count:          list[TrendPoint]

    # Data source provenance — new field, ignored by consumers that don't use it
    data_sources: DataSourcesResponse


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

def _get_patient_or_404(patient_id: int, db: Session) -> Patient:
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if not patient:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return patient


# ---------------------------------------------------------------------------
# Endpoint
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/summary", response_model=SummaryResponse)
def get_summary(
    patient_id: int,
    as_of_date: date | None = Query(
        default=None,
        description="End of the 30-day window (inclusive). Defaults to today.",
    ),
    db: Session = Depends(get_db),
):
    """
    Return a complete patient snapshot for the dashboard.

    The response is derived entirely from pre-computed DailyMetric rows and
    stored Alert rows — no metric recomputation happens here.  Run
    POST /api/v1/compute-metrics first to ensure the data is fresh.

    All `trend_*` arrays run oldest → newest so chart libraries can render
    them directly.  A `null` value in a trend point means no data was
    available for that day (device not worn, patient not registered yet, etc.).
    """
    _get_patient_or_404(patient_id, db)

    summary = build_patient_summary(db, patient_id, as_of_date)

    return SummaryResponse(
        patient_id=summary.patient_id,
        as_of_date=summary.as_of_date,
        window_days=summary.window_days,

        latest_independence_score=summary.latest_independence_score,
        latest_wandering_count=summary.latest_wandering_count,
        latest_wrong_turn_count=summary.latest_wrong_turn_count,
        latest_movement_radius_m=summary.latest_movement_radius_m,
        latest_wear_hours=summary.latest_wear_hours,
        latest_fall_count=summary.latest_fall_count,

        open_alerts=[AlertRead.model_validate(a) for a in summary.open_alerts],

        trend_independence_score=[
            TrendPoint(metric_date=p.metric_date, value=p.value)
            for p in summary.trend_independence_score
        ],
        trend_wandering_count=[
            TrendPoint(metric_date=p.metric_date, value=p.value)
            for p in summary.trend_wandering_count
        ],
        trend_wrong_turn_count=[
            TrendPoint(metric_date=p.metric_date, value=p.value)
            for p in summary.trend_wrong_turn_count
        ],
        trend_movement_radius_m=[
            TrendPoint(metric_date=p.metric_date, value=p.value)
            for p in summary.trend_movement_radius_m
        ],
        trend_wear_hours=[
            TrendPoint(metric_date=p.metric_date, value=p.value)
            for p in summary.trend_wear_hours
        ],
        trend_fall_count=[
            TrendPoint(metric_date=p.metric_date, value=p.value)
            for p in summary.trend_fall_count
        ],

        data_sources=DataSourcesResponse(
            events=summary.data_sources.events,
            movement_radius=summary.data_sources.movement_radius,
            wear_adherence=summary.data_sources.wear_adherence,
        ),
    )
