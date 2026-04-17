"""
Metrics Admin API — on-demand metric computation trigger.

POST /api/v1/compute-metrics
    Compute and store DailyMetric rows for every patient across every date
    that has raw source data (LocationPoints or Events).

    Safe to call repeatedly — existing rows are overwritten with freshly
    computed values (upsert).  Intended for post-seed population and manual
    recomputation after data corrections.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.jobs.daily_metrics import compute_and_store_daily_metrics_for_all_patients

router = APIRouter()


class ComputeMetricsResult(BaseModel):
    patients:     int   # distinct patient IDs processed
    dates:        int   # distinct calendar dates encountered across all patients
    rows_created: int   # new DailyMetric rows inserted
    rows_updated: int   # existing DailyMetric rows overwritten
    errors:       int   # patient/date pairs that raised an exception


@router.post("/", response_model=ComputeMetricsResult, status_code=200)
def compute_metrics(db: Session = Depends(get_db)):
    """
    Compute daily metrics for all patients across all dates that have raw
    source data in the database.

    - Discovers active dates from LocationPoint and Event timestamps — no
      date range parameter required.
    - Processes each (patient, date) pair in ascending date order so that
      movement-radius decline baselines build correctly within a single run.
    - Upserts results: safe to call after seeding or after new data arrives.

    Returns a summary of what was written.
    """
    result = compute_and_store_daily_metrics_for_all_patients(db)
    return ComputeMetricsResult(**result)
