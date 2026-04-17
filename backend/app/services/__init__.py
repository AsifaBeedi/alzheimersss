"""
Service layer — business logic decoupled from HTTP and database concerns.

  event_service                — validates and persists inbound events (Layer 1)
  metric_service               — computes DailyMetric rows (Layer 2)
  summary_service              — aggregates metrics into ClinicalSummary rows (Layer 3)
  alert_service                — threshold evaluation and Alert creation
  synthetic_data_generator     — demo seed (not a production service)

Geo utilities live in app.utils.geo (pure functions, no DB dependency).
"""

from app.services.synthetic_data_generator import seed_demo_data

__all__ = ["seed_demo_data"]
