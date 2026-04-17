"""
Layer 3 — Clinical Summary Engine API.
Returns pre-computed summaries and triggers on-demand generation.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.clinical_summary import SummaryPeriod
from app.schemas import ClinicalSummaryRead

router = APIRouter()


@router.get("/{patient_id}/latest", response_model=ClinicalSummaryRead)
def get_latest_summary(
    patient_id: int,
    period: SummaryPeriod = Query(SummaryPeriod.WEEKLY),
    db: Session = Depends(get_db),
):
    # TODO: implement — return most recent ClinicalSummary for patient+period
    raise NotImplementedError


@router.post("/{patient_id}/generate", status_code=202)
def generate_summary(
    patient_id: int,
    period: SummaryPeriod = Query(SummaryPeriod.WEEKLY),
    db: Session = Depends(get_db),
):
    # TODO: implement — trigger Clinical Summary Engine
    raise NotImplementedError
