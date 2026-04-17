"""
SQLAlchemy ORM models — MITRA data layer.

Tables:
  Patient          — registered patients (name, age, gender, home coords, safe radius)
  LocationPoint    — raw GPS pings from the wearable (Layer 1 raw input)
  WearSession      — continuous wear blocks (start/end/duration_minutes)
  Event            — Layer 1 output: typed clinical incidents with metadata_json context
  DailyMetric      — Layer 2 output: wide row per patient per date, one column per metric
  Alert            — threshold-breach notifications with alert_type / status lifecycle
  ClinicalSummary  — Layer 3 output: domain scores + composite independence score per period

Shared enums (app.models.enums):
  Severity    — info / warning / critical  (used by Event and Alert)
  EventType   — WANDERING_EPISODE / WRONG_TURN / FALL / AGITATION
  AlertType   — WANDERING / WRONG_TURN / FALL / LOW_ADHERENCE / LOW_INDEPENDENCE / AGITATION
  AlertStatus — open / acknowledged / resolved
"""

from app.models.enums import Severity, EventType, AlertType, AlertStatus  # noqa: F401
from app.models.patient import Patient
from app.models.location_point import LocationPoint
from app.models.wear_session import WearSession
from app.models.event import Event
from app.models.daily_metric import DailyMetric
from app.models.alert import Alert
from app.models.clinical_summary import ClinicalSummary

__all__ = [
    # Enums
    "Severity",
    "EventType",
    "AlertType",
    "AlertStatus",
    # Models
    "Patient",
    "LocationPoint",
    "WearSession",
    "Event",
    "DailyMetric",
    "Alert",
    "ClinicalSummary",
]
