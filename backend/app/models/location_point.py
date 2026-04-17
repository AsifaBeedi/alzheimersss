"""
Raw GPS ping from the wearable — Layer 1 raw input.
Written continuously during wear; drives wandering detection, movement radius,
and wrong-turn analysis in the Metric Engine.
"""

from datetime import datetime
from sqlalchemy import Float, DateTime, ForeignKey, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class LocationPoint(Base):
    __tablename__ = "location_points"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)

    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=func.now(), index=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    # Enriched by the Event Engine on ingest via haversine against patient.home_lat/lng
    speed_mps: Mapped[float | None] = mapped_column(Float, nullable=True)
    heading_deg: Mapped[float | None] = mapped_column(Float, nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="location_points")
