"""
Nightly job — Layer 2 Metric Engine.
Iterates over all patients and recomputes DailyMetrics for yesterday (or a given date).

Called by a scheduler (e.g. APScheduler, cron) or manually via the recompute endpoint.
"""

import logging
from datetime import date, timedelta

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.patient import Patient
from app.services import metric_service

logger = logging.getLogger(__name__)


def run_metric_compute(target_date: date | None = None) -> dict:
    """
    Compute DailyMetric rows for every patient on `target_date`.

    Args:
        target_date: The calendar date to (re)compute. Defaults to yesterday.

    Returns:
        A summary dict with keys: target_date, patients_processed, errors.
    """
    if target_date is None:
        target_date = date.today() - timedelta(days=1)

    db: Session = SessionLocal()
    patients_processed = 0
    errors: list[str] = []

    try:
        patients = db.query(Patient).order_by(Patient.id).all()
        logger.info(
            "Metric compute job starting: %d patients, target_date=%s",
            len(patients),
            target_date,
        )

        for patient in patients:
            try:
                metric_service.compute_for_date(db, patient.id, target_date)
                patients_processed += 1
                logger.debug("  patient_id=%d — done", patient.id)
            except Exception as exc:
                msg = f"patient_id={patient.id}: {exc}"
                logger.error("  %s", msg)
                errors.append(msg)

    finally:
        db.close()

    logger.info(
        "Metric compute job complete: %d/%d processed, %d errors",
        patients_processed,
        patients_processed + len(errors),
        len(errors),
    )
    return {
        "target_date": target_date.isoformat(),
        "patients_processed": patients_processed,
        "errors": errors,
    }
