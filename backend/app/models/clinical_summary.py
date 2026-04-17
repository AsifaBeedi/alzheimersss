"""
Layer 3 — Clinical Summary Engine output.

One summary per patient per period (weekly / monthly / quarterly).
Aggregates DailyMetric rows into domain scores and the composite independence score.
Source for both the Quarterly Clinical PDF and the Monthly Family Report.
"""

import enum
from datetime import date
from sqlalchemy import Date, Float, String, ForeignKey, Enum as SAEnum, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class SummaryPeriod(str, enum.Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"


class ClinicalSummary(Base):
    __tablename__ = "clinical_summaries"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)

    period: Mapped[SummaryPeriod] = mapped_column(SAEnum(SummaryPeriod), nullable=False)
    period_start: Mapped[date] = mapped_column(Date, nullable=False)
    period_end: Mapped[date] = mapped_column(Date, nullable=False)

    # 0–100 domain scores derived from DailyMetric averages over the period
    mobility_score: Mapped[float] = mapped_column(Float, nullable=True)
    safety_score: Mapped[float] = mapped_column(Float, nullable=True)
    adherence_score: Mapped[float] = mapped_column(Float, nullable=True)
    orientation_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Top-line composite (weighted roll-up of domain scores)
    composite_independence_score: Mapped[float] = mapped_column(Float, nullable=True)

    # Change alerts: list of strings describing significant changes vs previous period
    change_alerts: Mapped[list] = mapped_column(JSON, nullable=True, default=list)

    # Raw metric averages stored for PDF rendering without re-querying
    metric_snapshot: Mapped[dict] = mapped_column(JSON, nullable=True, default=dict)

    patient: Mapped["Patient"] = relationship(back_populates="clinical_summaries")
