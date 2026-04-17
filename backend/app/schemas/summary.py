"""
PatientSummaryRead — single-shot response for the dashboard.

Aggregates patient details, the most recent daily metric row, open alerts,
and a configurable window of metric history for sparklines — all in one
API call so the frontend doesn't need to fan out multiple requests.
"""

from pydantic import BaseModel
from app.schemas.patient import PatientRead
from app.schemas.daily_metric import DailyMetricRead
from app.schemas.alert import AlertRead


class PatientSummaryRead(BaseModel):
    patient: PatientRead

    # Most recent DailyMetric row — null if no metrics computed yet
    latest_metric: DailyMetricRead | None

    # OPEN alerts only, newest first
    active_alerts: list[AlertRead]

    # Ordered oldest→newest; used by frontend sparklines (default: last 30 days)
    metric_trend: list[DailyMetricRead]

    model_config = {"from_attributes": True}
