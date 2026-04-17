"""
Alert generation job.

generate_alerts_for_patient(db, patient_id)
    Iterate every stored DailyMetric date for one patient and run the full
    alert-rule suite via alert_engine.evaluate_and_create_alerts.

generate_alerts_for_all_patients(db)
    Call the per-patient function for every patient in the database and
    return an aggregate summary dict.

Deduplication is handled inside alert_engine._create_if_not_exists:
each (patient_id, alert_type, rule_key, metric_date) combination is only
ever written once regardless of how many times this job is called.

Dates are processed in ascending order per patient so that the 7-day
sliding-window checks (wandering frequency, wear adherence) accumulate
correctly — the same order used when metrics were originally computed.
"""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

from app.models.daily_metric import DailyMetric
from app.models.patient import Patient
from app.services.alert_engine import evaluate_and_create_alerts

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Per-patient
# ---------------------------------------------------------------------------

def generate_alerts_for_patient(db: Session, patient_id: int) -> dict:
    """
    Evaluate all alert rules for every DailyMetric date stored for one patient.

    Args:
        db:          Active SQLAlchemy session.
        patient_id:  Patient to process.

    Returns:
        {
            "patient_id":      int,
            "dates_evaluated": int,   — DailyMetric rows inspected
            "alerts_created":  int,   — new Alert rows written
            "errors":          int,   — dates that raised an exception
        }
    """
    metric_dates = (
        db.query(DailyMetric.metric_date)
        .filter(DailyMetric.patient_id == patient_id)
        .order_by(DailyMetric.metric_date.asc())
        .all()
    )

    dates_evaluated = 0
    alerts_created  = 0
    errors          = 0

    for (metric_date,) in metric_dates:
        try:
            new_alerts = evaluate_and_create_alerts(db, patient_id, metric_date)
            alerts_created  += len(new_alerts)
            dates_evaluated += 1
        except Exception:
            logger.exception(
                "Alert evaluation failed for patient_id=%d date=%s",
                patient_id, metric_date,
            )
            errors += 1

    logger.info(
        "generate_alerts_for_patient: patient_id=%d — %d dates, %d alerts, %d errors",
        patient_id, dates_evaluated, alerts_created, errors,
    )
    return {
        "patient_id":      patient_id,
        "dates_evaluated": dates_evaluated,
        "alerts_created":  alerts_created,
        "errors":          errors,
    }


# ---------------------------------------------------------------------------
# All patients
# ---------------------------------------------------------------------------

def generate_alerts_for_all_patients(db: Session) -> dict:
    """
    Generate alerts for every patient in the database.

    Iterates patients in primary-key order.  Each patient's dates are
    processed in ascending order so sliding-window rules are evaluated
    correctly.

    Returns:
        {
            "patients":        int,
            "dates_evaluated": int,
            "alerts_created":  int,
            "errors":          int,
        }
    """
    patients = db.query(Patient).order_by(Patient.id).all()
    if not patients:
        logger.warning("generate_alerts_for_all_patients: no patients found")
        return {"patients": 0, "dates_evaluated": 0, "alerts_created": 0, "errors": 0}

    total_dates   = 0
    total_alerts  = 0
    total_errors  = 0

    for patient in patients:
        result = generate_alerts_for_patient(db, patient.id)
        total_dates  += result["dates_evaluated"]
        total_alerts += result["alerts_created"]
        total_errors += result["errors"]

    logger.info(
        "generate_alerts_for_all_patients: %d patients, %d dates, %d alerts, %d errors",
        len(patients), total_dates, total_alerts, total_errors,
    )
    return {
        "patients":        len(patients),
        "dates_evaluated": total_dates,
        "alerts_created":  total_alerts,
        "errors":          total_errors,
    }
