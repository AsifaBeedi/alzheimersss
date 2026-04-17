"""
MITRA Metric Engine — Layer 2 pure-computation module.

compute_daily_metrics(db, patient_id, target_date) → DailyMetrics

Reads Event, LocationPoint, WearSession, and DailyMetric rows from the
database and returns a DailyMetrics dataclass.  No writes are performed here;
persistence (upsert into daily_metrics table) is the caller's responsibility.

Metric definitions
──────────────────
wandering_episode_count
    WANDERING_EPISODE events whose metadata_json.subtype == "wandering_episode_started".
    Counting only start events avoids double-counting the paired ended event.

wrong_turn_count
    WRONG_TURN events whose metadata_json.subtype == "wrong_turn_detected".

movement_radius_m
    Maximum haversine distance from the patient's home across all LocationPoints
    recorded on target_date.  None when the patient has no home coordinates or
    no GPS data for the day.

wear_hours
    Sum of WearSession.duration_minutes / 60 for sessions whose start_time falls
    on target_date and whose duration is known (duration_minutes is not NULL).

fall_count
    FALL events whose metadata_json.subtype == "fall_detected" (confirmed falls).
    Near-falls (subtype == "near_fall_detected") are excluded.

independence_score
    0–100 composite computed by utils/scoring.py using the five metrics above
    plus a movement-radius decline percentage derived from recent DailyMetric rows.

Helper
──────
estimate_radius_decline_pct(db, patient_id, anchor_date) → float
    Compares the 7-day mean radius ending on anchor_date to the mean of the
    preceding 7 days (days 8–14 before anchor_date).  Returns 0.0 when either
    window has insufficient data.  Uses pre-computed DailyMetric rows, so the
    window must contain already-written rows to return a non-zero result.
"""

from __future__ import annotations

import dataclasses
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
# Result type
# ---------------------------------------------------------------------------

@dataclasses.dataclass(slots=True)
class DailyMetrics:
    """All 6 Phase 1 metrics for one patient on one calendar date."""

    patient_id: int
    metric_date: date

    wandering_episode_count: int        # 0+ episodes that started on this date
    wrong_turn_count: int               # 0+ wrong-turn detections
    movement_radius_m: float | None     # None = no home coords or no GPS data
    wear_hours: float | None            # None = no WearSession rows (data absent); 0.0 = sessions exist but sum to zero
    fall_count: int                     # 0+ confirmed falls (near-falls excluded)
    independence_score: float           # 0–100; higher is more independent


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def compute_daily_metrics(
    db: Session,
    patient_id: int,
    target_date: date,
) -> DailyMetrics:
    """
    Compute all 6 Phase 1 metrics for one patient on one calendar date.

    Args:
        db:           Active SQLAlchemy session.
        patient_id:   Primary key of the patient to compute for.
        target_date:  Calendar date to evaluate.

    Returns:
        A DailyMetrics dataclass.  The database is not modified.

    Raises:
        ValueError: if patient_id does not exist.
    """
    patient = db.query(Patient).filter(Patient.id == patient_id).first()
    if patient is None:
        raise ValueError(f"Patient {patient_id} not found")

    day_start = datetime.combine(target_date, time.min)   # 00:00:00.000000
    day_end   = datetime.combine(target_date, time.max)   # 23:59:59.999999

    wander_count = _wandering_episode_count(db, patient_id, day_start, day_end)
    wrong_turns  = _wrong_turn_count(db, patient_id, day_start, day_end)
    radius_m     = _movement_radius_m(db, patient, day_start, day_end)
    hours_worn   = _wear_hours(db, patient_id, day_start, day_end)
    falls        = _fall_count(db, patient_id, day_start, day_end)

    decline_pct  = estimate_radius_decline_pct(db, patient_id, target_date)

    score = compute_independence_score(
        wandering_count=wander_count,
        wrong_turn_count=wrong_turns,
        movement_radius_decline_pct=decline_pct,
        wear_hours=hours_worn,
        fall_count=falls,
    )

    return DailyMetrics(
        patient_id=patient_id,
        metric_date=target_date,
        wandering_episode_count=wander_count,
        wrong_turn_count=wrong_turns,
        movement_radius_m=radius_m,
        wear_hours=hours_worn,
        fall_count=falls,
        independence_score=round(score, 2),
    )


def estimate_radius_decline_pct(
    db: Session,
    patient_id: int,
    anchor_date: date,
) -> float:
    """
    Estimate how much the patient's movement radius has declined recently.

    Method — two non-overlapping 7-day windows:

        prior  window: [anchor_date − 13 days, anchor_date − 7 days]   (days 8–14 before anchor)
        recent window: [anchor_date − 6 days,  anchor_date]            (days 0–6)

        decline = max(0, (mean_prior − mean_recent) / mean_prior × 100)

    A positive result means the patient is moving less than the prior week.
    Negative values (patient moving more) are clamped to 0.0 — no bonus.

    Uses pre-computed DailyMetric.movement_radius_m rows.  Returns 0.0 when
    either window contains no non-null rows, so early days of tracking receive
    no radius-decline penalty.

    Args:
        db:          Active SQLAlchemy session.
        patient_id:  Patient to evaluate.
        anchor_date: The date being computed (inclusive end of the recent window).

    Returns:
        A float in [0, 100]; 0.0 when insufficient history exists.
    """
    recent_start = anchor_date - timedelta(days=6)
    prior_end    = recent_start - timedelta(days=1)
    prior_start  = prior_end - timedelta(days=6)

    recent_rows = (
        db.query(DailyMetric.movement_radius_m)
        .filter(
            DailyMetric.patient_id == patient_id,
            DailyMetric.metric_date >= recent_start,
            DailyMetric.metric_date <= anchor_date,
            DailyMetric.movement_radius_m.isnot(None),
        )
        .all()
    )

    prior_rows = (
        db.query(DailyMetric.movement_radius_m)
        .filter(
            DailyMetric.patient_id == patient_id,
            DailyMetric.metric_date >= prior_start,
            DailyMetric.metric_date <= prior_end,
            DailyMetric.movement_radius_m.isnot(None),
        )
        .all()
    )

    if not recent_rows or not prior_rows:
        return 0.0

    mean_recent = sum(r.movement_radius_m for r in recent_rows) / len(recent_rows)
    mean_prior  = sum(r.movement_radius_m for r in prior_rows)  / len(prior_rows)

    if mean_prior <= 0.0:
        return 0.0

    return max(0.0, (mean_prior - mean_recent) / mean_prior * 100.0)


# ---------------------------------------------------------------------------
# Individual metric helpers (private)
# ---------------------------------------------------------------------------

def _wandering_episode_count(
    db: Session,
    patient_id: int,
    day_start: datetime,
    day_end: datetime,
) -> int:
    """
    Count WANDERING_EPISODE events that *started* on this day.

    The data layer produces a paired start + end event for every episode.
    Only the start event (subtype == "wandering_episode_started") is counted
    so each episode contributes exactly 1 to the total, regardless of whether
    the ended event falls on the same day or the next.
    """
    events = (
        db.query(Event)
        .filter(
            Event.patient_id == patient_id,
            Event.event_type == EventType.WANDERING_EPISODE,
            Event.timestamp >= day_start,
            Event.timestamp <= day_end,
        )
        .all()
    )
    return sum(
        1 for e in events
        if (e.metadata_json or {}).get("subtype") == "wandering_episode_started"
    )


def _wrong_turn_count(
    db: Session,
    patient_id: int,
    day_start: datetime,
    day_end: datetime,
) -> int:
    """
    Count WRONG_TURN events with subtype "wrong_turn_detected" on this day.

    Each event represents one navigation deviation; the subtype filter guards
    against any future administrative WRONG_TURN events (e.g. corrections)
    that should not affect the metric.
    """
    events = (
        db.query(Event)
        .filter(
            Event.patient_id == patient_id,
            Event.event_type == EventType.WRONG_TURN,
            Event.timestamp >= day_start,
            Event.timestamp <= day_end,
        )
        .all()
    )
    return sum(
        1 for e in events
        if (e.metadata_json or {}).get("subtype") == "wrong_turn_detected"
    )


def _movement_radius_m(
    db: Session,
    patient: Patient,
    day_start: datetime,
    day_end: datetime,
) -> float | None:
    """
    Return the maximum haversine distance (metres) from the patient's home
    across every GPS ping recorded on this day.

    Returns None in two cases:
      - the patient has no registered home coordinates
      - no LocationPoint rows exist for this day

    None is distinct from 0.0 (which would mean the patient was recorded
    at home all day) and signals missing data to the caller.
    """
    if patient.home_lat is None or patient.home_lng is None:
        return None

    loc_points = (
        db.query(LocationPoint)
        .filter(
            LocationPoint.patient_id == patient.id,
            LocationPoint.timestamp >= day_start,
            LocationPoint.timestamp <= day_end,
        )
        .all()
    )
    if not loc_points:
        return None

    coords = [CoordPair(p.lat, p.lng) for p in loc_points]
    return max_distance_from_home(patient.home_lat, patient.home_lng, coords)


def _wear_hours(
    db: Session,
    patient_id: int,
    day_start: datetime,
    day_end: datetime,
) -> float | None:
    """
    Sum WearSession.duration_minutes for sessions that started on this day.

    Only closed sessions (duration_minutes IS NOT NULL) are included; an open
    session means the device is still being worn and has no usable duration yet.

    Attributes the full session duration to the day it started.  Sessions that
    span midnight are rare in practice (the device is typically removed at night)
    and simple start-day attribution keeps the logic deterministic.

    Returns None when no qualifying sessions exist — distinguishes "no telemetry
    yet" from 0.0 ("sessions recorded but sum to zero hours").  Callers must
    treat None as absent data rather than zero wear.
    """
    sessions = (
        db.query(WearSession)
        .filter(
            WearSession.patient_id == patient_id,
            WearSession.start_time >= day_start,
            WearSession.start_time <= day_end,
            WearSession.duration_minutes.isnot(None),
        )
        .all()
    )
    if not sessions:
        return None
    return sum(s.duration_minutes for s in sessions) / 60.0


def _fall_count(
    db: Session,
    patient_id: int,
    day_start: datetime,
    day_end: datetime,
) -> int:
    """
    Count confirmed FALL events (subtype == "fall_detected") on this day.

    Near-falls (subtype == "near_fall_detected") share the same EventType.FALL
    but carry confirmed=False and a different subtype.  They represent a risk
    signal rather than an actual fall and are intentionally excluded from this
    metric to avoid inflating the penalty in the independence score.
    """
    events = (
        db.query(Event)
        .filter(
            Event.patient_id == patient_id,
            Event.event_type == EventType.FALL,
            Event.timestamp >= day_start,
            Event.timestamp <= day_end,
        )
        .all()
    )
    return sum(
        1 for e in events
        if (e.metadata_json or {}).get("subtype") == "fall_detected"
    )
