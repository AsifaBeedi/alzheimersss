"""
Independence Score computation — pure functions, no DB access.

Design:
  Start at 100 (fully independent), subtract weighted penalties for clinical
  events and missed adherence. Penalties are capped per category so a single
  bad metric cannot zero the score on its own; the combined worst-case is
  exactly 100 points, mapping to a final score of 0.

Penalty budget (must sum to 100):
  Wandering episodes      up to  30 pts
  Fall events             up to  30 pts
  Wrong turn count        up to  20 pts
  Low wear hours          up to  15 pts
  Movement radius decline up to  15 pts
  ─────────────────────────────────────
  Total worst-case              100 pts

These weights are intentionally simple and transparent so clinical advisors
can adjust the constants without touching the logic.
"""


# ---------------------------------------------------------------------------
# Constants — adjust here, not in the formula
# ---------------------------------------------------------------------------

_WANDERING_PENALTY_PER_EPISODE = 10.0   # deducted per episode
_WANDERING_PENALTY_CAP = 30.0

_FALL_PENALTY_PER_EVENT = 15.0          # falls are high-severity
_FALL_PENALTY_CAP = 30.0

_WRONG_TURN_PENALTY_PER_EVENT = 5.0
_WRONG_TURN_PENALTY_CAP = 20.0

_WEAR_PENALTY_MAX = 15.0                # full penalty when 0 hours worn
_WEAR_EXPECTED_HOURS = 8.0              # daily target for full wear score

_RADIUS_DECLINE_PENALTY_MAX = 15.0     # full penalty at 100% radius decline


# ---------------------------------------------------------------------------
# Public functions
# ---------------------------------------------------------------------------

def clamp_score(value: float, min_value: float = 0.0, max_value: float = 100.0) -> float:
    """Clamp value to [min_value, max_value]."""
    return max(min_value, min(max_value, value))


def compute_independence_score(
    wandering_count: int,
    wrong_turn_count: int,
    movement_radius_decline_pct: float,
    wear_hours: float | None,
    fall_count: int,
) -> float:
    """
    Compute a 0–100 independence score for a single patient-day.

    Args:
        wandering_count:
            Number of WANDERING_EPISODE events recorded that day.
        wrong_turn_count:
            Number of WRONG_TURN events recorded that day.
        movement_radius_decline_pct:
            How much the patient's movement radius shrank relative to their
            personal 30-day rolling baseline, expressed as 0–100 percent.
            0 = same or greater radius (no decline), 100 = stayed at home.
        wear_hours:
            Total hours the device was worn that day.  None means no wear-session
            data is available yet (hybrid demo / JSONL-only); the wear penalty is
            skipped entirely so missing telemetry doesn't distort the score.
        fall_count:
            Number of FALL events recorded that day.

    Returns:
        A float in [0, 100]. Higher is more independent.
    """
    score = 100.0

    # --- Safety events ---------------------------------------------------
    wandering_penalty = min(wandering_count * _WANDERING_PENALTY_PER_EPISODE, _WANDERING_PENALTY_CAP)
    fall_penalty = min(fall_count * _FALL_PENALTY_PER_EVENT, _FALL_PENALTY_CAP)

    # --- Navigation errors -----------------------------------------------
    wrong_turn_penalty = min(wrong_turn_count * _WRONG_TURN_PENALTY_PER_EVENT, _WRONG_TURN_PENALTY_CAP)

    # --- Wear adherence --------------------------------------------------
    # Linear ramp: 0 penalty at _WEAR_EXPECTED_HOURS or above; full penalty at 0 hours.
    # None means no telemetry available yet (hybrid/JSONL-only) — no penalty applied.
    if wear_hours is None:
        wear_penalty = 0.0
    elif wear_hours >= _WEAR_EXPECTED_HOURS:
        wear_penalty = 0.0
    else:
        wear_penalty = (1.0 - wear_hours / _WEAR_EXPECTED_HOURS) * _WEAR_PENALTY_MAX

    # --- Mobility decline ------------------------------------------------
    # Clamp the input to [0, 100] defensively before scaling.
    decline_pct = clamp_score(movement_radius_decline_pct, 0.0, 100.0)
    radius_penalty = (decline_pct / 100.0) * _RADIUS_DECLINE_PENALTY_MAX

    score -= wandering_penalty + fall_penalty + wrong_turn_penalty + wear_penalty + radius_penalty

    return clamp_score(score)
