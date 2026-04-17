"""
Alert Engine service.
Evaluates DailyMetric values against configured thresholds and creates Alert rows.
Called by MetricService after each recompute.
"""

from sqlalchemy.orm import Session


# Threshold map — metric_name → (warning_threshold, critical_threshold)
# Direction: "high" means exceeding threshold is bad; "low" means falling below is bad.
THRESHOLDS = {
    "wandering_episode_count": {"direction": "high", "warning": 1, "critical": 3},
    "wrong_turn_count":        {"direction": "high", "warning": 2, "critical": 5},
    "fall_event_count":        {"direction": "high", "warning": 1, "critical": 2},
    "wear_adherence_hours":    {"direction": "low",  "warning": 6, "critical": 3},
    "movement_radius_m":       {"direction": "low",  "warning": 200, "critical": 100},
    "composite_independence_score": {"direction": "low", "warning": 50, "critical": 30},
}


class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def evaluate(self, patient_id: int, metric_name: str, value: float):
        """
        Check value against THRESHOLDS; create an Alert row if threshold is breached.
        TODO: implement
        """
        raise NotImplementedError
