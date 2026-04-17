"""
A continuous block of device wear — the basis for Wear Adherence metrics.
One session per uninterrupted wearing block; end_time is null while live.
duration_minutes is derived and stored on session close.
"""

from datetime import datetime
from sqlalchemy import Float, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class WearSession(Base):
    __tablename__ = "wear_sessions"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)

    start_time: Mapped[datetime] = mapped_column(DateTime, nullable=False, index=True)
    end_time: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Stored in minutes; summed by MetricService to produce daily wear_hours
    duration_minutes: Mapped[float | None] = mapped_column(Float, nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="wear_sessions")
