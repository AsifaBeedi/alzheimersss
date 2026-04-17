"""
Layer 2 — Metric Engine output.

Wide table: one row per patient per calendar date, one column per Phase 1 metric.
The Metric Engine job upserts this row nightly from Event and WearSession data.

Design note — wide vs EAV:
  A wide table is used deliberately. The 6 Phase 1 metrics are fixed and known;
  a wide schema makes dashboard queries trivial (SELECT * WHERE patient_id AND date)
  and avoids pivot logic in the frontend. Phase 2 metrics can extend this table
  with nullable columns added via Alembic migrations.
"""

from datetime import date
from sqlalchemy import Date, Float, Integer, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class DailyMetric(Base):
    __tablename__ = "daily_metrics"
    __table_args__ = (
        # One row per patient per day — upsert pattern in MetricService
        UniqueConstraint("patient_id", "metric_date", name="uq_patient_metric_date"),
    )

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    patient_id: Mapped[int] = mapped_column(ForeignKey("patients.id"), nullable=False, index=True)
    metric_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)

    # --- Phase 1 metrics -------------------------------------------------
    # All nullable: a metric is null if insufficient data exists for that day
    # (e.g. device not worn, <1 hour of data).

    # Wandering Episodes (metric 3) — count of WANDERING_EPISODE events that day
    wandering_episode_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Wrong Turn Count (metric 5) — count of WRONG_TURN events that day
    wrong_turn_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Movement Radius Trend (metric 4) — max haversine distance from home (metres)
    movement_radius_m: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Wear Adherence (metric 7) — total hours worn that day (sum of WearSession.duration_minutes / 60)
    wear_hours: Mapped[float | None] = mapped_column(Float, nullable=True)

    # Fall Events with Context (metric 9) — count of FALL events that day
    fall_count: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Composite Independence Score (metric 10) — 0–100, computed by SummaryService
    independence_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    patient: Mapped["Patient"] = relationship(back_populates="daily_metrics")
