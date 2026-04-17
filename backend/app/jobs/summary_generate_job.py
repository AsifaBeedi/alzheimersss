"""
Weekly / monthly job — Layer 3 Clinical Summary Engine.
Generates ClinicalSummary rows for all patients.
"""

from datetime import date
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.clinical_summary import SummaryPeriod
from app.services.summary_service import SummaryService


def run_summary_generate(period: SummaryPeriod = SummaryPeriod.WEEKLY, as_of: date | None = None):
    """
    Entry point called by the scheduler or the /summary/{id}/generate endpoint.
    TODO: implement — iterate patients, call SummaryService.generate
    """
    if as_of is None:
        as_of = date.today()

    db: Session = SessionLocal()
    try:
        service = SummaryService(db)
        # TODO: query all patient IDs and call service.generate
        raise NotImplementedError
    finally:
        db.close()
