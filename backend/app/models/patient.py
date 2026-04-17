from datetime import datetime
from sqlalchemy import String, Float, Integer, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class Patient(Base):
    __tablename__ = "patients"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    age: Mapped[int] = mapped_column(Integer, nullable=False)

    # Free-text — clinical systems use varied gender representation
    gender: Mapped[str | None] = mapped_column(String(30), nullable=True)

    # Home coordinates — origin point for wandering radius calculations
    home_lat: Mapped[float | None] = mapped_column(Float, nullable=True)
    home_lng: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Patient-specific safe zone radius; overrides the global config default
    safe_radius_m: Mapped[float] = mapped_column(Float, nullable=False, default=200.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    location_points: Mapped[list["LocationPoint"]] = relationship(back_populates="patient")
    wear_sessions: Mapped[list["WearSession"]] = relationship(back_populates="patient")
    events: Mapped[list["Event"]] = relationship(back_populates="patient")
    daily_metrics: Mapped[list["DailyMetric"]] = relationship(back_populates="patient")
    alerts: Mapped[list["Alert"]] = relationship(back_populates="patient")
    clinical_summaries: Mapped[list["ClinicalSummary"]] = relationship(back_populates="patient")
