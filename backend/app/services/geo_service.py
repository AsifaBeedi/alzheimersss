"""
Geospatial utilities for MITRA.
Pure functions — no DB access. Used by EventService and MetricService.
"""

import math


def haversine_distance(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Return great-circle distance in metres between two WGS-84 coordinates.
    """
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def is_wandering(distance_from_home_m: float, threshold_m: float) -> bool:
    """Return True if distance exceeds the configured wandering threshold."""
    return distance_from_home_m > threshold_m
