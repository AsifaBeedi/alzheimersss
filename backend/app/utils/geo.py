"""
Geospatial utilities — pure functions, no DB access.

All distance calculations use the Haversine formula against WGS-84 coordinates.
Earth radius is fixed at the standard mean value (6,371,000 m); error is <0.5%
for the distances relevant to dementia monitoring (up to a few kilometres).
"""

import math
from typing import NamedTuple


# ---------------------------------------------------------------------------
# Core distance
# ---------------------------------------------------------------------------

def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """
    Return the great-circle distance in metres between two WGS-84 coordinates.

    Args:
        lat1, lng1: origin point (degrees)
        lat2, lng2: destination point (degrees)

    Returns:
        Distance in metres.
    """
    R = 6_371_000  # mean Earth radius, metres

    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


# ---------------------------------------------------------------------------
# Batch helpers
# ---------------------------------------------------------------------------

class CoordPair(NamedTuple):
    lat: float
    lng: float


def max_distance_from_home(
    home_lat: float,
    home_lng: float,
    points: list[CoordPair],
) -> float:
    """
    Return the maximum haversine distance (metres) between the patient's home
    and any point in the sequence.

    Args:
        home_lat, home_lng: patient's registered home coordinates
        points: sequence of CoordPair(lat, lng) namedtuples

    Returns:
        Maximum distance in metres, or 0.0 if the sequence is empty.

    Usage (from MetricService):
        coords = [CoordPair(p.lat, p.lng) for p in location_points]
        radius = max_distance_from_home(patient.home_lat, patient.home_lng, coords)
    """
    if not points:
        return 0.0
    return max(
        haversine_meters(home_lat, home_lng, p.lat, p.lng)
        for p in points
    )


# ---------------------------------------------------------------------------
# Safe-radius check
# ---------------------------------------------------------------------------

def is_outside_safe_radius(
    home_lat: float,
    home_lng: float,
    lat: float,
    lng: float,
    safe_radius_m: float,
) -> bool:
    """
    Return True if the given coordinate is farther from home than safe_radius_m.

    Used by the Event Engine to decide whether to open a wandering episode.
    The caller is responsible for the time-window confirmation step
    (patient must remain outside the radius for WANDERING_DETECTION_WINDOW_S
    seconds before an episode is recorded).
    """
    return haversine_meters(home_lat, home_lng, lat, lng) > safe_radius_m
