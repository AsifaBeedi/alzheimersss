"""
MITRA Synthetic Data Generator

Populates the database with two demo patients and 30 days of believable activity,
event, and daily metric data so the dashboard can render real computed graphs
without a live wearable.

Patient A — Margaret O'Brien, 74, mild cognitive decline
  Gradual movement radius shrink, ~weekly wandering, occasional wrong turns,
  good wear adherence, one near-fall, no confirmed falls.

Patient B — Thomas Greenfield, 81, moderate cognitive decline
  Stronger radius shrink, frequent wandering (~every 3 days), higher wrong-turn
  rate, fragmented wear, two near-falls, one confirmed fall, one emergency press.

Data is bit-for-bit reproducible: the RNG seed is reset to the same value at
the start of every seed_demo_data() call.

Real MITRA wearable data flows in through POST /api/v1/events — no generator
code needs to change when the live device is connected.
"""

import logging
import math
import random
from dataclasses import dataclass
from datetime import date, datetime, timedelta

from sqlalchemy.orm import Session

from app.models.patient import Patient
from app.models.location_point import LocationPoint
from app.models.wear_session import WearSession
from app.models.event import Event
from app.models.daily_metric import DailyMetric
from app.models.enums import EventType, Severity
from app.utils.geo import CoordPair, max_distance_from_home
from app.utils.scoring import compute_independence_score

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_SEED = 2024
_BASE_DATE = date(2026, 3, 17)      # day 0; 30-day window ends 2026-04-15
_DAYS = 30
_METRES_PER_DEG_LAT = 111_320       # WGS-84 approximation


# ---------------------------------------------------------------------------
# Patient profile spec
# ---------------------------------------------------------------------------

@dataclass
class _Profile:
    # Identity
    name: str
    age: int
    gender: str
    home_lat: float
    home_lng: float
    safe_radius_m: float

    # Movement radius: linear decline over 30 days ± daily noise
    start_radius_m: float
    end_radius_m: float
    radius_noise_m: float

    # Days (0-indexed) with specific clinical events
    wandering_days: list[int]       # WANDERING_EPISODE pair (start + end)
    wrong_turn_days: list[int]      # ≥1 WRONG_TURN event
    max_wrong_turns: int            # upper bound per wrong-turn day
    fall_days: list[int]            # confirmed FALL (severity=CRITICAL)
    near_fall_days: list[int]       # near-fall (severity=WARNING, confirmed=False)
    emergency_days: list[int]       # emergency button press (AGITATION)

    # Wear adherence
    wear_base_hours: float
    wear_noise_hours: float
    no_wear_days: list[int]         # device completely off — no events, no points
    short_wear_days: list[int]      # device worn but only 2–4 h

    # Outings
    no_outing_days: list[int]       # patient stays home (device may be worn)


# ---------------------------------------------------------------------------
# Clinical profiles
# ---------------------------------------------------------------------------

_PROFILE_A = _Profile(
    name="Margaret O'Brien",
    age=74,
    gender="female",
    home_lat=51.5074,
    home_lng=-0.1278,
    safe_radius_m=500.0,
    start_radius_m=480.0,
    end_radius_m=375.0,
    radius_noise_m=30.0,
    wandering_days=[6, 13, 20, 27],
    wrong_turn_days=[3, 6, 10, 13, 18, 20, 24, 27],
    max_wrong_turns=2,
    fall_days=[],
    near_fall_days=[17],
    emergency_days=[],
    wear_base_hours=8.5,
    wear_noise_hours=0.6,
    no_wear_days=[4, 22],
    short_wear_days=[9, 16],
    no_outing_days=[4, 11, 22],
)

_PROFILE_B = _Profile(
    name="Thomas Greenfield",
    age=81,
    gender="male",
    home_lat=51.5154,
    home_lng=-0.1755,
    safe_radius_m=400.0,
    start_radius_m=360.0,
    end_radius_m=150.0,
    radius_noise_m=28.0,
    wandering_days=[2, 6, 9, 13, 17, 21, 24, 28],
    wrong_turn_days=[1, 4, 6, 9, 12, 15, 17, 19, 21, 25, 29],
    max_wrong_turns=4,
    fall_days=[15],
    near_fall_days=[8, 22],
    emergency_days=[28],
    wear_base_hours=5.8,
    wear_noise_hours=1.0,
    no_wear_days=[3, 11, 20, 26],
    short_wear_days=[5, 14, 23],
    no_outing_days=[3, 11, 20, 26],
)


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _day_date(day: int) -> date:
    return _BASE_DATE + timedelta(days=day)


def _day_dt(day: int, hour: int, minute: int = 0) -> datetime:
    d = _day_date(day)
    return datetime(d.year, d.month, d.day, hour, minute)


def _target_radius(profile: _Profile, day: int, rng: random.Random) -> float:
    """Linearly interpolated movement radius with Gaussian noise."""
    t = day / (_DAYS - 1)
    base = profile.start_radius_m + (profile.end_radius_m - profile.start_radius_m) * t
    return max(50.0, base + rng.gauss(0, profile.radius_noise_m))


def _outing_track(
    home_lat: float,
    home_lng: float,
    max_dist_m: float,
    start_dt: datetime,
    rng: random.Random,
) -> tuple[list[tuple], datetime]:
    """
    Generate an out-and-back GPS track from home.

    Returns:
        (points, end_dt) where each point is
        (lat, lng, timestamp, speed_mps, heading_deg).
    """
    lat_scale = math.cos(math.radians(home_lat))
    bearing = rng.uniform(0, 2 * math.pi)
    n_steps = max(4, int(max_dist_m / 85))
    speed = rng.uniform(0.9, 1.25)      # walking speed m/s

    pts: list[tuple] = []
    t = start_dt

    # --- Outward leg (home → max distance) ---
    for i in range(1, n_steps + 1):
        frac = i / n_steps
        dist = max(5.0, max_dist_m * frac + rng.gauss(0, max_dist_m * 0.025))
        b = bearing + rng.gauss(0, 0.08)
        lat = home_lat + (dist / _METRES_PER_DEG_LAT) * math.cos(b)
        lng = home_lng + (dist / (_METRES_PER_DEG_LAT * lat_scale)) * math.sin(b)
        t += timedelta(seconds=rng.uniform(280, 450))
        pts.append((round(lat, 7), round(lng, 7), t, round(speed, 2), round(math.degrees(b) % 360, 1)))

    # Linger at far point
    t += timedelta(minutes=rng.randint(8, 22))

    # --- Return leg (max distance → home) ---
    for i in range(n_steps - 1, -1, -1):
        frac = i / n_steps
        dist = max(0.0, max_dist_m * frac + rng.gauss(0, max_dist_m * 0.02))
        b = bearing + rng.gauss(0, 0.08)
        if dist < 5:
            lat = home_lat + rng.gauss(0, 0.00003)
            lng = home_lng + rng.gauss(0, 0.00003)
        else:
            lat = home_lat + (dist / _METRES_PER_DEG_LAT) * math.cos(b)
            lng = home_lng + (dist / (_METRES_PER_DEG_LAT * lat_scale)) * math.sin(b)
        t += timedelta(seconds=rng.uniform(280, 450))
        return_heading = round((math.degrees(b) + 180) % 360, 1)
        pts.append((round(lat, 7), round(lng, 7), t, round(speed, 2), return_heading))

    return pts, t


def _make_wear_sessions(
    patient: Patient,
    profile: _Profile,
    day: int,
    rng: random.Random,
) -> list[WearSession]:
    if day in profile.no_wear_days:
        return []

    if day in profile.short_wear_days:
        hours = rng.uniform(2.5, 3.8)
    else:
        hours = max(1.5, profile.wear_base_hours + rng.gauss(0, profile.wear_noise_hours))

    wake_hour = rng.randint(7, 9)
    start = _day_dt(day, wake_hour, rng.randint(0, 30))
    end = start + timedelta(hours=hours)

    return [WearSession(
        patient_id=patient.id,
        start_time=start,
        end_time=end,
        duration_minutes=round(hours * 60, 1),
    )]


def _make_location_points(
    patient: Patient,
    profile: _Profile,
    day: int,
    max_dist_m: float,
    wear_sessions: list[WearSession],
    rng: random.Random,
) -> list[LocationPoint]:
    if not wear_sessions:
        return []

    session = wear_sessions[0]

    # No outing: generate a few near-home points to represent indoor movement
    if day in profile.no_outing_days:
        pts = []
        t = session.start_time
        for _ in range(rng.randint(2, 4)):
            t += timedelta(hours=rng.uniform(1.5, 3.0))
            if session.end_time and t >= session.end_time:
                break
            pts.append(LocationPoint(
                patient_id=patient.id,
                timestamp=t,
                lat=round(profile.home_lat + rng.gauss(0, 0.00008), 7),
                lng=round(profile.home_lng + rng.gauss(0, 0.00008), 7),
                speed_mps=0.0,
                heading_deg=0.0,
            ))
        return pts

    # Wandering days: patient goes ~1.3× farther than their normal radius
    effective_dist = max_dist_m * 1.32 if day in profile.wandering_days else max_dist_m

    depart_dt = _day_dt(day, rng.randint(9, 11), rng.randint(0, 45))
    if depart_dt < session.start_time:
        depart_dt = session.start_time + timedelta(minutes=20)

    raw_pts, _ = _outing_track(profile.home_lat, profile.home_lng, effective_dist, depart_dt, rng)

    result = []
    for lat, lng, t, speed, heading in raw_pts:
        if session.end_time and t > session.end_time:
            break
        result.append(LocationPoint(
            patient_id=patient.id,
            timestamp=t,
            lat=lat,
            lng=lng,
            speed_mps=speed,
            heading_deg=heading,
        ))
    return result


def _make_events(
    patient: Patient,
    profile: _Profile,
    day: int,
    location_points: list[LocationPoint],
    rng: random.Random,
) -> list[Event]:
    # No device → no events
    if day in profile.no_wear_days:
        return []

    events: list[Event] = []

    # Anchor timestamp: middle of the outing, or mid-morning if no points
    if location_points:
        anchor = location_points[len(location_points) // 2].timestamp
        far_pt  = location_points[len(location_points) // 3]   # ~outward peak
    else:
        anchor = _day_dt(day, 10, rng.randint(0, 59))
        far_pt = None

    # --- Wandering episode (start + end pair) ----------------------------
    if day in profile.wandering_days:
        duration_s = rng.randint(720, 2400)    # 12–40 min episode
        t_start = anchor + timedelta(minutes=rng.randint(5, 20))
        t_end   = t_start + timedelta(seconds=duration_s)
        far_dist = round(profile.start_radius_m * rng.uniform(1.05, 1.45))

        events.append(Event(
            patient_id=patient.id,
            event_type=EventType.WANDERING_EPISODE,
            timestamp=t_start,
            severity=Severity.WARNING,
            lat=far_pt.lat if far_pt else None,
            lng=far_pt.lng if far_pt else None,
            metadata_json={
                "subtype": "wandering_episode_started",
                "max_distance_m": far_dist,
                "time_of_day": "morning" if t_start.hour < 12 else "afternoon",
            },
        ))
        events.append(Event(
            patient_id=patient.id,
            event_type=EventType.WANDERING_EPISODE,
            timestamp=t_end,
            severity=Severity.INFO,
            lat=far_pt.lat if far_pt else None,
            lng=far_pt.lng if far_pt else None,
            metadata_json={
                "subtype": "wandering_episode_ended",
                "duration_s": duration_s,
                "max_distance_m": far_dist,
                "reorientation_issued": True,
            },
        ))

    # --- Wrong turns -----------------------------------------------------
    if day in profile.wrong_turn_days:
        n = rng.randint(1, profile.max_wrong_turns)
        for i in range(n):
            t = anchor + timedelta(minutes=rng.randint(-25, 25) + i * 12)
            events.append(Event(
                patient_id=patient.id,
                event_type=EventType.WRONG_TURN,
                timestamp=t,
                severity=Severity.INFO,
                lat=far_pt.lat if far_pt else None,
                lng=far_pt.lng if far_pt else None,
                metadata_json={
                    "subtype": "wrong_turn_detected",
                    "deviation_m": rng.randint(25, 130),
                    "route": rng.choice(["pharmacy", "shop", "park", "post_office", "bus_stop"]),
                    "reorientation_issued": True,
                },
            ))

    # --- Confirmed fall --------------------------------------------------
    if day in profile.fall_days:
        t = anchor + timedelta(minutes=rng.randint(5, 35))
        events.append(Event(
            patient_id=patient.id,
            event_type=EventType.FALL,
            timestamp=t,
            severity=Severity.CRITICAL,
            lat=far_pt.lat if far_pt else None,
            lng=far_pt.lng if far_pt else None,
            metadata_json={
                "subtype": "fall_detected",
                "confirmed": True,
                "activity": rng.choice(["walking", "stepping_down", "turning"]),
                "surface": rng.choice(["pavement", "indoor_floor", "garden_path"]),
                "near_fall_history": len(profile.near_fall_days),
                "emergency_contacted": True,
            },
        ))

    # --- Near-fall -------------------------------------------------------
    if day in profile.near_fall_days:
        t = anchor + timedelta(minutes=rng.randint(-15, 15))
        events.append(Event(
            patient_id=patient.id,
            event_type=EventType.FALL,
            timestamp=t,
            severity=Severity.WARNING,
            lat=None,
            lng=None,
            metadata_json={
                "subtype": "near_fall_detected",
                "confirmed": False,
                "activity": rng.choice(["walking", "stepping_up", "turning"]),
                "recovered_independently": True,
            },
        ))

    # --- Emergency button press (AGITATION) ------------------------------
    if day in profile.emergency_days:
        t = anchor + timedelta(minutes=rng.randint(30, 60))
        events.append(Event(
            patient_id=patient.id,
            event_type=EventType.AGITATION,
            timestamp=t,
            severity=Severity.CRITICAL,
            lat=far_pt.lat if far_pt else None,
            lng=far_pt.lng if far_pt else None,
            metadata_json={
                "subtype": "emergency_button_pressed",
                "caregiver_notified": True,
                "response_time_min": rng.randint(4, 18),
            },
        ))

    return events


def _make_daily_metric(
    patient: Patient,
    profile: _Profile,
    day: int,
    events: list[Event],
    wear_sessions: list[WearSession],
    location_points: list[LocationPoint],
) -> DailyMetric:
    wear_hours = round(sum(s.duration_minutes or 0 for s in wear_sessions) / 60.0, 2)

    # On no-wear days record wear_hours=0 and leave clinical columns null
    # (gap in the chart signals the missing day honestly)
    if not wear_sessions:
        return DailyMetric(
            patient_id=patient.id,
            metric_date=_day_date(day),
            wear_hours=0.0,
        )

    # Event counts
    wandering_count = sum(
        1 for e in events
        if e.event_type == EventType.WANDERING_EPISODE
        and e.metadata_json.get("subtype") == "wandering_episode_started"
    )
    wrong_turn_count = sum(1 for e in events if e.event_type == EventType.WRONG_TURN)
    fall_count = sum(
        1 for e in events
        if e.event_type == EventType.FALL and e.metadata_json.get("confirmed") is True
    )

    # Movement radius from actual location points
    if location_points:
        coords = [CoordPair(p.lat, p.lng) for p in location_points]
        movement_radius_m = round(
            max_distance_from_home(profile.home_lat, profile.home_lng, coords), 1
        )
    else:
        movement_radius_m = 0.0

    # Radius decline vs day-0 baseline (used only for the independence score)
    decline_pct = max(
        0.0,
        (profile.start_radius_m - movement_radius_m) / profile.start_radius_m * 100,
    )

    score = compute_independence_score(
        wandering_count=wandering_count,
        wrong_turn_count=wrong_turn_count,
        movement_radius_decline_pct=decline_pct,
        wear_hours=wear_hours,
        fall_count=fall_count,
    )

    return DailyMetric(
        patient_id=patient.id,
        metric_date=_day_date(day),
        wandering_episode_count=wandering_count,
        wrong_turn_count=wrong_turn_count,
        movement_radius_m=movement_radius_m,
        wear_hours=wear_hours,
        fall_count=fall_count,
        independence_score=round(score, 1),
    )


def _generate_day(
    patient: Patient,
    profile: _Profile,
    day: int,
    rng: random.Random,
) -> tuple[list, list, list, DailyMetric]:
    max_dist = _target_radius(profile, day, rng)
    sessions = _make_wear_sessions(patient, profile, day, rng)
    points   = _make_location_points(patient, profile, day, max_dist, sessions, rng)
    events   = _make_events(patient, profile, day, points, rng)
    metric   = _make_daily_metric(patient, profile, day, events, sessions, points)
    return sessions, points, events, metric


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------

def seed_demo_data(db: Session) -> None:
    """
    Insert two demo patients and 30 days of synthetic data unless the patients
    table is already populated.

    Safe to call repeatedly — exits immediately when data is present.
    RNG seed is reset on every call so output is always identical.
    """
    if db.query(Patient).count() > 0:
        logger.info("Patients already exist — skipping demo seed.")
        return

    rng = random.Random(_SEED)
    logger.info("Seeding MITRA demo data: %d days × 2 patients…", _DAYS)

    for profile in (_PROFILE_A, _PROFILE_B):
        patient = Patient(
            name=profile.name,
            age=profile.age,
            gender=profile.gender,
            home_lat=profile.home_lat,
            home_lng=profile.home_lng,
            safe_radius_m=profile.safe_radius_m,
        )
        db.add(patient)
        db.flush()          # get patient.id before building related rows

        all_sessions: list[WearSession]    = []
        all_points:   list[LocationPoint]  = []
        all_events:   list[Event]          = []
        all_metrics:  list[DailyMetric]    = []

        for day in range(_DAYS):
            sessions, points, events, metric = _generate_day(patient, profile, day, rng)
            all_sessions.extend(sessions)
            all_points.extend(points)
            all_events.extend(events)
            all_metrics.append(metric)

        db.add_all(all_sessions)
        db.add_all(all_points)
        db.add_all(all_events)
        db.add_all(all_metrics)

        logger.info(
            "  %-22s  %2d sessions  %3d points  %2d events  %2d metrics",
            profile.name,
            len(all_sessions),
            len(all_points),
            len(all_events),
            len(all_metrics),
        )

    db.commit()
    logger.info("Demo seed complete.")
