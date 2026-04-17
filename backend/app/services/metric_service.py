"""
Layer 2 — Metric Engine service.
Aggregates Event, LocationPoint, and WearSession rows into DailyMetric rows
for a given patient and calendar date.

Public API:
  compute_for_date(db, patient_id, target_date)       → DailyMetric (upsert)
  compute_for_date_range(db, patient_id, from, to)    → list[DailyMetric]
  get_metrics_for_range(db, patient_id, from, to)     → list[DailyMetric]

Callable from:
  POST /api/v1/metrics/{id}/recompute  (on-demand, single day)
  app/jobs/metric_compute_job.py       (nightly batch, all patients × yesterday)

Metrics computed per patient-day:
  wandering_episode_count   count of WANDERING_EPISODE events
  wrong_turn_count          count of WRONG_TURN events
  movement_radius_m         max haversine distance from home across all LocationPoints
  wear_hours                sum of WearSession.duration_minutes / 60 for sessions starting that day
  fall_count                count of FALL events
  independence_score        0–100 composite score (see utils/scoring.py)
"""

from datetime import date, datetime, time, timedelta

from sqlalchemy.orm import Session

from app.models.daily_metric import DailyMetric
from app.models.enums import EventType
from app.models.event import Event
from app.models.location_point import LocationPoint
from app.models.patient import Patient
from app.models.wear_session import WearSession
from app.utils.geo import CoordPair, max_distance_from_home
from app.utils.scoring import compute_independence_score


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def compute_for_date(db: Session, patient_id: int, target_date: date) -> DailyMetric:
    """
    Compute (or recompute) all DailyMetric columns for one patient on one date.
    Upserts the resulting row — creates if absent, overwrites if present.

    Raises ValueError if patient_id does not exist.
    Returns the upserted DailyMetric ORM object (already committed).
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise ValueError(f"Patient {patient_id} not found")

    day_start = datetime.combine(target_date, time.min)
    day_end   = datetime.combine(target_date, time.max)

    # ------------------------------------------------------------------
    # 1. Clinical event counts
    # ------------------------------------------------------------------
    events_today = (
        db.query(Event)
        .filter(
            Event.patient_id == patient_id,
            Event.timestamp >= day_start,
            Event.timestamp <= day_end,
        )
        .all()
    )

    wandering_episode_count = sum(
        1 for e in events_today if e.event_type == EventType.WANDERING_EPISODE
    )
    wrong_turn_count = sum(
        1 for e in events_today if e.event_type == EventType.WRONG_TURN
    )
    fall_count = sum(
        1 for e in events_today if e.event_type == EventType.FALL
    )

    # ------------------------------------------------------------------
    # 2. Movement radius — max distance from home across all GPS pings
    # ------------------------------------------------------------------
    movement_radius_m: float | None = None
    if patient.home_lat is not None and patient.home_lng is not None:
        loc_points = (
            db.query(LocationPoint)
            .filter(
                LocationPoint.patient_id == patient_id,
                LocationPoint.timestamp >= day_start,
                LocationPoint.timestamp <= day_end,
            )
            .all()
        )
        if loc_points:
            coords = [CoordPair(p.lat, p.lng) for p in loc_points]
            movement_radius_m = max_distance_from_home(
                patient.home_lat, patient.home_lng, coords
            )

    # ------------------------------------------------------------------
    # 3. Wear adherence — sessions whose start_time falls on target_date.
    #    Sessions with null duration_minutes (still open) are excluded.
    # ------------------------------------------------------------------
    wear_sessions = (
        db.query(WearSession)
        .filter(
            WearSession.patient_id == patient_id,
            WearSession.start_time >= day_start,
            WearSession.start_time <= day_end,
            WearSession.duration_minutes.isnot(None),
        )
        .all()
    )
    wear_hours = (
        sum(s.duration_minutes for s in wear_sessions) / 60.0
        if wear_sessions else 0.0
    )

    # ------------------------------------------------------------------
    # 4. Independence score
    #    Requires movement radius decline pct vs. 30-day rolling baseline.
    # ------------------------------------------------------------------
    radius_decline_pct = _compute_radius_decline_pct(
        db, patient_id, target_date, movement_radius_m
    )
    independence_score = compute_independence_score(
        wandering_count=wandering_episode_count,
        wrong_turn_count=wrong_turn_count,
        movement_radius_decline_pct=radius_decline_pct,
        wear_hours=wear_hours,
        fall_count=fall_count,
    )

    # ------------------------------------------------------------------
    # 5. Upsert — update existing row or insert new one
    # ------------------------------------------------------------------
    existing = (
        db.query(DailyMetric)
        .filter(
            DailyMetric.patient_id == patient_id,
            DailyMetric.metric_date == target_date,
        )
        .first()
    )

    if existing:
        existing.wandering_episode_count = wandering_episode_count
        existing.wrong_turn_count        = wrong_turn_count
        existing.movement_radius_m       = movement_radius_m
        existing.wear_hours              = wear_hours
        existing.fall_count              = fall_count
        existing.independence_score      = independence_score
        row = existing
    else:
        row = DailyMetric(
            patient_id=patient_id,
            metric_date=target_date,
            wandering_episode_count=wandering_episode_count,
            wrong_turn_count=wrong_turn_count,
            movement_radius_m=movement_radius_m,
            wear_hours=wear_hours,
            fall_count=fall_count,
            independence_score=independence_score,
        )
        db.add(row)

    db.commit()
    db.refresh(row)
    return row


def compute_for_date_range(
    db: Session,
    patient_id: int,
    from_date: date,
    to_date: date,
) -> list[DailyMetric]:
    """
    Compute DailyMetric for every calendar date in [from_date, to_date] inclusive.
    Processes dates in ascending order so each day's radius-decline baseline can
    see the rows already upserted for earlier days in the same range.
    Returns the list of upserted rows.
    """
    results: list[DailyMetric] = []
    current = from_date
    while current <= to_date:
        row = compute_for_date(db, patient_id, current)
        results.append(row)
        current += timedelta(days=1)
    return results


def get_metrics_for_range(
    db: Session,
    patient_id: int,
    from_date: date,
    to_date: date,
) -> list[DailyMetric]:
    """
    Return pre-computed DailyMetric rows for a patient in [from_date, to_date].
    Rows are ordered by metric_date ascending (chronological chart order).
    Does NOT recompute — call compute_for_date_range first if needed.
    """
    return (
        db.query(DailyMetric)
        .filter(
            DailyMetric.patient_id == patient_id,
            DailyMetric.metric_date >= from_date,
            DailyMetric.metric_date <= to_date,
        )
        .order_by(DailyMetric.metric_date.asc())
        .all()
    )


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _compute_radius_decline_pct(
    db: Session,
    patient_id: int,
    target_date: date,
    today_radius_m: float | None,
) -> float:
    """
    Return how much today's movement radius has declined relative to the
    patient's personal 30-day rolling average (days strictly before target_date).

    Returns 0.0 when:
      - today_radius_m is None (no location data today)
      - no prior rows exist yet (first days of tracking)
      - baseline average is 0.0 (patient never left home previously)

    A positive return value means the patient moved less than usual.
    Negative values are clamped to 0.0 (moving more than baseline = no penalty).
    """
    if today_radius_m is None:
        return 0.0

    baseline_start = target_date - timedelta(days=30)

    prior_radii = (
        db.query(DailyMetric.movement_radius_m)
        .filter(
            DailyMetric.patient_id == patient_id,
            DailyMetric.metric_date >= baseline_start,
            DailyMetric.metric_date < target_date,
            DailyMetric.movement_radius_m.isnot(None),
        )
        .all()
    )

    if not prior_radii:
        return 0.0

    baseline_m = sum(r.movement_radius_m for r in prior_radii) / len(prior_radii)
    if baseline_m <= 0.0:
        return 0.0

    decline = (baseline_m - today_radius_m) / baseline_m * 100.0
    return max(0.0, decline)
