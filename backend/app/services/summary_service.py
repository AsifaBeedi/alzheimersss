"""
Layer 3 — Clinical Summary Engine service.
Aggregates DailyMetric rows over a period into domain scores and the composite independence score.

Domain score weightings (placeholder — to be validated clinically):
  mobility_score     = f(movement_radius_m, wear_adherence_hours)
  safety_score       = f(fall_event_count, wandering_episode_count)
  adherence_score    = f(wear_adherence_hours)
  orientation_score  = f(wrong_turn_count, wandering_episode_count)

  composite = 0.30 * mobility + 0.30 * safety + 0.20 * adherence + 0.20 * orientation
"""

from datetime import date
from sqlalchemy.orm import Session
from app.models.clinical_summary import SummaryPeriod


class SummaryService:
    def __init__(self, db: Session):
        self.db = db

    def generate(self, patient_id: int, period: SummaryPeriod, as_of: date):
        """
        Compute and persist a ClinicalSummary for the period ending on as_of.
        Returns the persisted ClinicalSummary.
        TODO: implement
        """
        raise NotImplementedError

    def compute_composite_score(self, metric_averages: dict) -> float:
        """
        Pure function — takes a dict of metric averages, returns 0–100 composite.
        TODO: implement weighting logic
        """
        raise NotImplementedError
