"""
Shared utility functions — pure, no DB access.

  geo         — haversine distance, radius checks, batch helpers
  scoring     — independence score computation
  date_utils  — period boundary helpers (week / month / quarter)
"""

from app.utils.geo import haversine_meters, max_distance_from_home, is_outside_safe_radius, CoordPair
from app.utils.scoring import clamp_score, compute_independence_score
from app.utils.date_utils import week_bounds, month_bounds, quarter_bounds

__all__ = [
    # geo
    "CoordPair",
    "haversine_meters",
    "max_distance_from_home",
    "is_outside_safe_radius",
    # scoring
    "clamp_score",
    "compute_independence_score",
    # date utils
    "week_bounds",
    "month_bounds",
    "quarter_bounds",
]
