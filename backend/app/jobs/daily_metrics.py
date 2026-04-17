"""
Daily metric aggregation job — Layer 2 persistence.

compute_and_store_daily_metrics_for_patient(db, patient_id, target_date)
    Compute metrics via metric_engine and upsert the DailyMetric row.
    Returns (row, created): created=True for a new row, False for an update.

compute_and_store_daily_metrics_for_all_patients(db)
    Discover every (patient, date) pair that has raw source data and run
    the per-patient function for each.  Dates are sourced from LocationPoint
    and Event timestamps so no manual date range needs to be passed in.
    Returns a summary dict suitable for returning directly from an API response.
"""

from __future__ import annotations

import logging
from datetime import date
from collections import defaultdict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.daily_metric import DailyMetric
from app.models.event import Event
from app.models.location_point import LocationPoint
from app.models.patient import Patient
from app.services.metric_engine import compute_daily_metrics

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-patient / per-date
# ---------------------------------------------------------------------------

def compute_and_store_daily_metrics_for_patient(
    db: Session,
    patient_id: int,
    target_date: date,
) -> tuple[DailyMetric, bool]:
    """
    Compute all 6 Phase 1 metrics for one patient on one date and upsert the
    result into the DailyMetric table.

    Args:
        db:           Active SQLAlchemy session (caller owns the lifecycle).
        patient_id:   Patient to compute for.
        target_date:  Calendar date to evaluate.

    Returns:
        (row, created) where created=True means a new row was inserted and
        False means an existing row was overwritten.

    Raises:
        ValueError: propagated from metric_engine if patient_id is invalid.
    """
    metrics = compute_daily_metrics(db, patient_id, target_date)

    existing: DailyMetric | None = (
        db.query(DailyMetric)
        .filter(
            DailyMetric.patient_id == patient_id,
            DailyMetric.metric_date == target_date,
        )
        .first()
    )

    created = existing is None

    if existing:
        existing.wandering_episode_count = metrics.wandering_episode_count
        existing.wrong_turn_count        = metrics.wrong_turn_count
        existing.movement_radius_m       = metrics.movement_radius_m
        existing.wear_hours              = metrics.wear_hours
        existing.fall_count              = metrics.fall_count
        existing.independence_score      = metrics.independence_score
        row = existing
    else:
        row = DailyMetric(
            patient_id=patient_id,
            metric_date=target_date,
            wandering_episode_count=metrics.wandering_episode_count,
            wrong_turn_count=metrics.wrong_turn_count,
            movement_radius_m=metrics.movement_radius_m,
            wear_hours=metrics.wear_hours,
            fall_count=metrics.fall_count,
            independence_score=metrics.independence_score,
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return row, created


# ---------------------------------------------------------------------------
# Batch — all patients × all dates with source data
# ---------------------------------------------------------------------------

def compute_and_store_daily_metrics_for_all_patients(db: Session) -> dict:
    """
    Discover every (patient_id, date) combination that has raw source data
    (LocationPoints or Events) and compute/store a DailyMetric row for each.

    Dates are derived from existing LocationPoint and Event timestamps, so the
    function works with both the synthetic demo data and live wearable data
    without needing a hard-coded date range.

    Dates are processed in ascending order per patient so that each day's
    radius-decline baseline can see the rows already written for earlier days
    in the same run.

    Returns:
        {
            "patients":     int  — distinct patient IDs processed,
            "dates":        int  — distinct calendar dates encountered,
            "rows_created": int  — new DailyMetric rows inserted,
            "rows_updated": int  — existing DailyMetric rows overwritten,
            "errors":       int  — patient/date pairs that raised an exception,
        }
    """
    patients = db.query(Patient).order_by(Patient.id).all()
    if not patients:
        logger.warning("compute_and_store_daily_metrics_for_all_patients: no patients found")
        return {"patients": 0, "dates": 0, "rows_created": 0, "rows_updated": 0, "errors": 0}

    patient_ids = {p.id for p in patients}

    # Collect distinct dates per patient from both source tables.
    # func.date() returns a "YYYY-MM-DD" string in SQLite.
    patient_dates: dict[int, set[date]] = defaultdict(set)

    for pid, d_str in db.query(
        LocationPoint.patient_id,
        func.date(LocationPoint.timestamp),
    ).distinct().all():
        if pid in patient_ids:
            patient_dates[pid].add(_to_date(d_str))

    for pid, d_str in db.query(
        Event.patient_id,
        func.date(Event.timestamp),
    ).distinct().all():
        if pid in patient_ids:
            patient_dates[pid].add(_to_date(d_str))

    rows_created = 0
    rows_updated = 0
    errors       = 0
    all_dates: set[date] = set()

    for patient_id in sorted(patient_ids):
        dates = sorted(patient_dates.get(patient_id, []))  # ascending → baseline builds correctly
        for d in dates:
            all_dates.add(d)
            try:
                _, created = compute_and_store_daily_metrics_for_patient(db, patient_id, d)
                if created:
                    rows_created += 1
                else:
                    rows_updated += 1
            except Exception:
                logger.exception(
                    "Failed to compute metrics for patient_id=%d date=%s", patient_id, d
                )
                errors += 1

    logger.info(
        "Batch complete: %d patients, %d dates, %d created, %d updated, %d errors",
        len(patient_ids), len(all_dates), rows_created, rows_updated, errors,
    )
    return {
        "patients":     len(patient_ids),
        "dates":        len(all_dates),
        "rows_created": rows_created,
        "rows_updated": rows_updated,
        "errors":       errors,
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _to_date(value: object) -> date:
    """
    Coerce the value returned by func.date() to a Python date.

    SQLite returns "YYYY-MM-DD" strings; other backends may return date
    objects directly.  Both are handled here so the batch function is
    backend-agnostic.
    """
    if isinstance(value, date):
        return value
    return date.fromisoformat(str(value))
