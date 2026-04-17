"""
Layer 1 — Event Engine output.

One row per detected clinical incident. The Event Engine writes these from
raw LocationPoint and WearSession data; the Metric Engine counts them into
DailyMetric columns.

metadata_json payload examples by event_type:
  WANDERING_EPISODE → {"duration_s": 180, "max_distance_m": 420, "time_of_day": "night"}
  WRONG_TURN        → {"route": "pharmacy", "deviation_m": 65, "reorientation_issued": true}
  FALL              → {"activity": "walking", "location": "pavement", "near_fall_history": 2}
  AGITATION         → {"trigger": "emergency_button", "duration_s": 40}
"""

from datetime import datetime
from sqlalchemy import DateTime, Float, ForeignKey, JSON, Enum as SAEnum, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.models.enums import EventType, Severity


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)

    event_type: Mapped[EventType] = mapped_column(
        SAEnum(EventType, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        index=True,
    )
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), index=True)
    severity: Mapped[Severity] = mapped_column(
        SAEnum(Severity, values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        default=Severity.INFO,
    )

    # Optional spatial context — null for non-location events (e.g. agitation via button press)
    lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Flexible event-specific context — see module docstring for payload shapes per event_type
    metadata_json: Mapped[dict | None] = mapped_column(JSON, nullable=True, default=dict)

    patient: Mapped["Patient"] = relationship(back_populates="events")
