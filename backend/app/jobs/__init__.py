"""
Background jobs — scheduled tasks that run outside the request/response cycle.

  metric_compute_job   — nightly: recompute DailyMetrics for all patients
  summary_generate_job — weekly/monthly: generate ClinicalSummary rows
  seed_data_job        — one-shot: populate DB with synthetic demo data
"""

from app.jobs.metric_compute_job import run_metric_compute
from app.jobs.summary_generate_job import run_summary_generate
from app.jobs.seed_data_job import run_seed

__all__ = ["run_metric_compute", "run_summary_generate", "run_seed"]
