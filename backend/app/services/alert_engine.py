"""
MITRA Alert Engine — threshold evaluation and alert persistence.

evaluate_and_create_alerts(db, patient_id, target_date) → list[Alert]

Evaluates six alert rules against the stored DailyMetric rows for a patient
and creates Alert rows for any threshold breaches that have not already been
recorded for the same date.

Alert rules
───────────
Rule                     AlertType          Trigger basis
────────────────────────────────────────────────────────────────────────────
wandering_frequency      WANDERING          7-day episode sum ≥ threshold
wrong_turn_frequency     LOW_INDEPENDENCE   7-day wrong-turn sum ≥ threshold
movement_radius_decline  LOW_INDEPENDENCE   week-over-week radius decline ≥ %
wear_adherence           LOW_ADHERENCE      7-day mean wear hours < threshold
fall_detected            FALL               target_date fall_count > 0
independence_score       LOW_INDEPENDENCE   target_date score < threshold
────────────────────────────────────────────────────────────────────────────

Deduplication
─────────────
Each alert is identified by (patient_id, alert_type, rule_key, metric_date).
`rule_key` is stored in metadata_json so that multiple LOW_INDEPENDENCE rules
("wrong_turn_frequency", "movement_radius_decline", "independence_score") can
coexist on the same day without creating duplicates on repeated calls.
"""

from __future__ import annotations

import logging
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.alert import Alert
from app.models.daily_metric import DailyMetric
from app.models.enums import AlertStatus, AlertType, Severity

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Thresholds — edit here, not in the logic
# ---------------------------------------------------------------------------

# Wandering frequency: rolling 7-day episode count
WANDERING_WARNING_COUNT  = 2   # ≥ 2 episodes in the past 7 days → WARNING
WANDERING_CRITICAL_COUNT = 4   # ≥ 4 episodes                     → CRITICAL

# Movement radius decline: week-over-week percentage drop
RADIUS_DECLINE_WARNING_PCT  = 20.0  # ≥ 20 % decline vs prior 7 days → WARNING
RADIUS_DECLINE_CRITICAL_PCT = 40.0  # ≥ 40 %                          → CRITICAL

# Wrong turn frequency: rolling 7-day event count
WRONG_TURN_WARNING_COUNT  = 3   # ≥ 3 detections in 7 days → WARNING
WRONG_TURN_CRITICAL_COUNT = 6   # ≥ 6 detections           → CRITICAL

# Wear adherence: rolling 7-day mean wear hours
WEAR_WARNING_HOURS  = 5.0   # mean < 5 h  → WARNING
WEAR_CRITICAL_HOURS = 3.0   # mean < 3 h  → CRITICAL

# Independence score: single-day value
INDEPENDENCE_WARNING_SCORE  = 60.0  # score < 60 → WARNING
INDEPENDENCE_CRITICAL_SCORE = 40.0  # score < 40 → CRITICAL

# How many days back to look for the rolling windows
_WINDOW_DAYS = 7


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def evaluate_and_create_alerts(
    db: Session,
    patient_id: int,
    target_date: date,
) -> list[Alert]:
    """
    Run all alert rules for one patient on one date.

    Reads DailyMetric rows from the database; does not recompute them.
    Call compute_and_store_daily_metrics_for_patient first to ensure the
    target_date row exists.

    Returns a list of newly created Alert ORM objects (already committed).
    An empty list means no thresholds were breached, or all breaches were
    already recorded from a previous call.
    """
    target_metric = (
        db.query(DailyMetric)
        .filter(
            DailyMetric.patient_id == patient_id,
            DailyMetric.metric_date == target_date,
        )
        .first()
    )
    if target_metric is None:
        logger.debug(
            "evaluate_and_create_alerts: no DailyMetric row for patient_id=%d date=%s — skipping",
            patient_id, target_date,
        )
        return []

    new_alerts: list[Alert] = []

    checks = [
        _check_wandering_frequency(db, patient_id, target_date),
        _check_wrong_turn_frequency(db, patient_id, target_date),
        _check_radius_decline(db, patient_id, target_date),
        _check_wear_adherence(db, patient_id, target_date),
        _check_fall(target_metric, target_date),
        _check_independence_score(target_metric, target_date),
    ]

    for result in checks:
        if result is None:
            continue
        alert_type, severity, description, metadata = result
        alert = _create_if_not_exists(db, patient_id, alert_type, severity, description, metadata)
        if alert is not None:
            new_alerts.append(alert)

    if new_alerts:
        logger.info(
            "Created %d alert(s) for patient_id=%d date=%s",
            len(new_alerts), patient_id, target_date,
        )
    return new_alerts


# ---------------------------------------------------------------------------
# Alert rule checks
# Each returns (alert_type, severity, description, metadata_json) or None.
# ---------------------------------------------------------------------------

def _check_wandering_frequency(
    db: Session,
    patient_id: int,
    target_date: date,
) -> tuple | None:
    """
    Raise WANDERING if the 7-day episode count meets or exceeds a threshold.
    Looks at [target_date - 6, target_date] inclusive.
    """
    window_start = target_date - timedelta(days=_WINDOW_DAYS - 1)
    rows = (
        db.query(DailyMetric.wandering_episode_count)
        .filter(
            DailyMetric.patient_id == patient_id,
            DailyMetric.metric_date >= window_start,
            DailyMetric.metric_date <= target_date,
            DailyMetric.wandering_episode_count.isnot(None),
        )
        .all()
    )
    if not rows:
        return None

    total = sum(r.wandering_episode_count for r in rows)

    if total >= WANDERING_CRITICAL_COUNT:
        severity = Severity.CRITICAL
    elif total >= WANDERING_WARNING_COUNT:
        severity = Severity.WARNING
    else:
        return None

    return (
        AlertType.WANDERING,
        severity,
        f"Wandering frequency rising: {total} episode(s) in the past {_WINDOW_DAYS} days.",
        {"rule_key": "wandering_frequency", "metric_date": target_date.isoformat(),
         "window_days": _WINDOW_DAYS, "episode_count": total},
    )


def _check_wrong_turn_frequency(
    db: Session,
    patient_id: int,
    target_date: date,
) -> tuple | None:
    """
    Raise LOW_INDEPENDENCE if the 7-day wrong-turn count meets or exceeds a threshold.
    Looks at [target_date - 6, target_date] inclusive.

    Wrong turns are a direct navigation-safety signal from the pipeline.  The
    independence score already penalises them (5 pts/event, cap 20 pts), but
    that penalty alone cannot breach the score warning threshold — so a
    dedicated rolling-window check is needed to surface consistent route
    confusion.
    """
    window_start = target_date - timedelta(days=_WINDOW_DAYS - 1)
    rows = (
        db.query(DailyMetric.wrong_turn_count)
        .filter(
            DailyMetric.patient_id == patient_id,
            DailyMetric.metric_date >= window_start,
            DailyMetric.metric_date <= target_date,
            DailyMetric.wrong_turn_count.isnot(None),
        )
        .all()
    )
    if not rows:
        return None

    total = sum(r.wrong_turn_count for r in rows)

    if total >= WRONG_TURN_CRITICAL_COUNT:
        severity = Severity.CRITICAL
    elif total >= WRONG_TURN_WARNING_COUNT:
        severity = Severity.WARNING
    else:
        return None

    return (
        AlertType.LOW_INDEPENDENCE,
        severity,
        f"Navigation confusion rising: {total} wrong-turn detection(s) in the past {_WINDOW_DAYS} days.",
        {"rule_key": "wrong_turn_frequency", "metric_date": target_date.isoformat(),
         "window_days": _WINDOW_DAYS, "wrong_turn_count": total},
    )


def _check_radius_decline(
    db: Session,
    patient_id: int,
    target_date: date,
) -> tuple | None:
    """
    Raise LOW_INDEPENDENCE(radius) if the 7-day mean movement radius has
    declined by ≥ threshold% compared to the prior 7-day mean.
    """
    recent_start = target_date - timedelta(days=_WINDOW_DAYS - 1)
    prior_end    = recent_start - timedelta(days=1)
    prior_start  = prior_end   - timedelta(days=_WINDOW_DAYS - 1)

    def _mean_radius(from_d: date, to_d: date) -> float | None:
        rows = (
            db.query(DailyMetric.movement_radius_m)
            .filter(
                DailyMetric.patient_id == patient_id,
                DailyMetric.metric_date >= from_d,
                DailyMetric.metric_date <= to_d,
                DailyMetric.movement_radius_m.isnot(None),
            )
            .all()
        )
        if not rows:
            return None
        return sum(r.movement_radius_m for r in rows) / len(rows)

    mean_recent = _mean_radius(recent_start, target_date)
    mean_prior  = _mean_radius(prior_start, prior_end)

    if mean_recent is None or mean_prior is None or mean_prior <= 0.0:
        return None

    decline_pct = (mean_prior - mean_recent) / mean_prior * 100.0
    if decline_pct < RADIUS_DECLINE_WARNING_PCT:
        return None

    severity = (
        Severity.CRITICAL if decline_pct >= RADIUS_DECLINE_CRITICAL_PCT
        else Severity.WARNING
    )
    return (
        AlertType.LOW_INDEPENDENCE,
        severity,
        f"Movement radius declining: {decline_pct:.1f}% reduction vs prior {_WINDOW_DAYS} days "
        f"(recent mean {mean_recent:.0f} m vs prior {mean_prior:.0f} m).",
        {"rule_key": "movement_radius_decline", "metric_date": target_date.isoformat(),
         "decline_pct": round(decline_pct, 1),
         "mean_recent_m": round(mean_recent, 1), "mean_prior_m": round(mean_prior, 1)},
    )


def _check_wear_adherence(
    db: Session,
    patient_id: int,
    target_date: date,
) -> tuple | None:
    """
    Raise LOW_ADHERENCE if the 7-day rolling mean of wear_hours is below threshold.
    """
    window_start = target_date - timedelta(days=_WINDOW_DAYS - 1)
    rows = (
        db.query(DailyMetric.wear_hours)
        .filter(
            DailyMetric.patient_id == patient_id,
            DailyMetric.metric_date >= window_start,
            DailyMetric.metric_date <= target_date,
            DailyMetric.wear_hours.isnot(None),
        )
        .all()
    )
    if not rows:
        return None

    mean_hours = sum(r.wear_hours for r in rows) / len(rows)

    if mean_hours < WEAR_CRITICAL_HOURS:
        severity = Severity.CRITICAL
    elif mean_hours < WEAR_WARNING_HOURS:
        severity = Severity.WARNING
    else:
        return None

    return (
        AlertType.LOW_ADHERENCE,
        severity,
        f"Low device wear adherence: {mean_hours:.1f} h/day average over the past {_WINDOW_DAYS} days "
        f"(target ≥ {WEAR_WARNING_HOURS:.0f} h/day).",
        {"rule_key": "wear_adherence", "metric_date": target_date.isoformat(),
         "mean_wear_hours": round(mean_hours, 2), "window_days": _WINDOW_DAYS},
    )


def _check_fall(
    metric: DailyMetric,
    target_date: date,
) -> tuple | None:
    """
    Raise FALL if one or more confirmed falls were recorded on target_date.
    Single fall → WARNING; multiple falls → CRITICAL.
    """
    if not metric.fall_count:
        return None

    severity = Severity.CRITICAL if metric.fall_count > 1 else Severity.WARNING
    return (
        AlertType.FALL,
        severity,
        f"{metric.fall_count} confirmed fall(s) detected on {target_date}.",
        {"rule_key": "fall_detected", "metric_date": target_date.isoformat(),
         "fall_count": metric.fall_count},
    )


def _check_independence_score(
    metric: DailyMetric,
    target_date: date,
) -> tuple | None:
    """
    Raise LOW_INDEPENDENCE(score) if the composite independence score is below threshold.
    """
    if metric.independence_score is None:
        return None

    score = metric.independence_score

    if score < INDEPENDENCE_CRITICAL_SCORE:
        severity = Severity.CRITICAL
    elif score < INDEPENDENCE_WARNING_SCORE:
        severity = Severity.WARNING
    else:
        return None

    return (
        AlertType.LOW_INDEPENDENCE,
        severity,
        f"Independence score low: {score:.1f}/100 on {target_date} "
        f"(threshold: warning < {INDEPENDENCE_WARNING_SCORE:.0f}, "
        f"critical < {INDEPENDENCE_CRITICAL_SCORE:.0f}).",
        {"rule_key": "independence_score", "metric_date": target_date.isoformat(),
         "score": score},
    )


# ---------------------------------------------------------------------------
# Persistence helper
# ---------------------------------------------------------------------------

def _create_if_not_exists(
    db: Session,
    patient_id: int,
    alert_type: AlertType,
    severity: Severity,
    description: str,
    metadata: dict,
) -> Alert | None:
    """
    Create and commit an Alert row only if no OPEN or ACKNOWLEDGED alert with
    the same (patient_id, alert_type, rule_key, metric_date) already exists.

    Returns the new Alert on insert, or None if a duplicate was found.
    """
    rule_key    = metadata.get("rule_key", "")
    metric_date = metadata.get("metric_date", "")

    existing = (
        db.query(Alert)
        .filter(
            Alert.patient_id == patient_id,
            Alert.alert_type == alert_type,
            Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
        )
        .all()
    )
    for a in existing:
        m = a.metadata_json or {}
        if m.get("rule_key") == rule_key and m.get("metric_date") == metric_date:
            return None   # already recorded

    alert = Alert(
        patient_id=patient_id,
        alert_type=alert_type,
        severity=severity,
        description=description,
        timestamp=datetime.utcnow(),
        status=AlertStatus.OPEN,
        metadata_json=metadata,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert
