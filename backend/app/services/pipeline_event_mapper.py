"""
MITRA pipeline JSONL -> Event row mapper.

The upstream file is expected to be JSONL where each line is a record shaped
roughly like:

{
  "ts": "...",
  "status": "...",
  "response_type": "...",
  "frame_id": "...",
  "feature_ids_detected": [...],
  "payload": {
    "frame_id": "...",
    "device_id": "...",
    "scene_type": "...",
    "scene_name": "...",
    "pedestrian_count": 2,
    "emergency": {
      "level": "...",
      "action": "...",
      "message": "..."
    },
    "feature_outputs": {...},
    "processing_time_ms": 123,
    "gpu2_results": {...},
    "gpu3_response": {...}
  }
}

Mapping goals:
- keep one explainable Event row per source record
- preserve the original upstream record in metadata_json
- map pipeline signals to metric-driving EventType values
- set metadata_json["subtype"] so the metric engine counts events correctly

Event type mapping (priority order):
  FALL               fall_detected       emergency block + fall/safety signal
  FALL               fall_detected       confirmed fall keyword in signals
  FALL               near_fall_detected  fall keyword only, no emergency block
  WANDERING_EPISODE  wandering_episode_started  outdoor / boundary / lost signals
  WRONG_TURN         wrong_turn_detected navigation / route / disorientation signals
  AGITATION          emergency_button_pressed   emergency block, no specific category
  AGITATION          pipeline_event      no matching signal (does not affect metrics)

The metric engine counts:
  wandering_episode_count  ← WANDERING_EPISODE + subtype "wandering_episode_started"
  wrong_turn_count         ← WRONG_TURN        + subtype "wrong_turn_detected"
  fall_count               ← FALL              + subtype "fall_detected"
  (near_fall_detected is stored but intentionally excluded from fall_count)
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
from typing import Any

from app.models.enums import EventType, Severity


PatientResolver = Callable[[Mapping[str, Any]], int | None]

# ---------------------------------------------------------------------------
# Severity classification
# ---------------------------------------------------------------------------

_CRITICAL_LEVELS = {"critical", "high", "severe", "emergency"}
_WARNING_LEVELS  = {"warning", "warn", "medium", "moderate", "elevated"}

_EMERGENCY_HINTS = (
    "ambulance", "emergency", "urgent", "critical", "immediate", "dispatch", "911",
)

# ---------------------------------------------------------------------------
# Event-type signal hints
# (all matched case-insensitively against a concatenated signal blob)
# ---------------------------------------------------------------------------

# Fall — confirmed: emergency block + any fall hint → fall_detected (counted)
# Fall — keyword only → near_fall_detected (visible in timeline, not counted)
_FALL_CONFIRMED_HINTS = (
    "fall detected",
    "fallen",
    "collapse",
    "fell",
)
_FALL_HINTS = (
    "fall",
    "slip",
    "trip",
    "injury",
    "ground impact",
    "impact detected",
    "unsafe landing",
)

# Wandering — outdoor / boundary / prolonged behaviour → wandering_episode_started
_WANDERING_HINTS = (
    "wander",
    "wandering",
    "lost",
    "missing",
    "geofence",
    "boundary",
    "outside safe",
    "unsafe area",
    "prolonged",
    "exit zone",
    "away from home",
    "left safe",
)

# Wrong turn — navigation / route confusion → wrong_turn_detected
_WRONG_TURN_HINTS = (
    "wrong turn",
    "wrong direction",
    "route deviation",
    "navigation error",
    "incorrect route",
    "disoriented",
    "wrong path",
    "took wrong",
    "incorrect path",
    "navigation",
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------

@dataclass(slots=True, frozen=True)
class PipelineEventRow:
    patient_id:    int
    event_type:    EventType
    timestamp:     datetime
    severity:      Severity
    lat:           float | None
    lng:           float | None
    metadata_json: dict[str, Any]

    def to_insert_dict(self) -> dict[str, Any]:
        return {
            "patient_id":    self.patient_id,
            "event_type":    self.event_type,
            "timestamp":     self.timestamp,
            "severity":      self.severity,
            "lat":           self.lat,
            "lng":           self.lng,
            "metadata_json": self.metadata_json,
        }

    def to_event_model(self):
        from app.models.event import Event
        return Event(**self.to_insert_dict())


# ---------------------------------------------------------------------------
# Public: JSONL parsing
# ---------------------------------------------------------------------------

def iter_pipeline_records(path: str | Path) -> Iterator[dict[str, Any]]:
    source_path = Path(path)
    with source_path.open("r", encoding="utf-8") as handle:
        for line_number, raw_line in enumerate(handle, start=1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                record = json.loads(line)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"Invalid JSON on line {line_number} of {source_path}"
                ) from exc
            if not isinstance(record, dict):
                raise ValueError(
                    f"Expected object JSON on line {line_number} of {source_path}"
                )
            yield record


# ---------------------------------------------------------------------------
# Public: single-record mapper
# ---------------------------------------------------------------------------

def map_pipeline_record_to_event_row(
    record: Mapping[str, Any],
    *,
    default_patient_id:  int | None              = None,
    device_patient_map:  Mapping[str, int] | None = None,
    patient_resolver:    PatientResolver | None   = None,
) -> PipelineEventRow:

    payload   = _as_mapping(record.get("payload"))
    emergency = _as_mapping(payload.get("emergency"))

    patient_id = _resolve_patient_id(
        record, payload,
        default_patient_id=default_patient_id,
        device_patient_map=device_patient_map,
        patient_resolver=patient_resolver,
    )

    timestamp = _coerce_timestamp(
        _first_non_empty(
            record.get("ts"),
            record.get("timestamp"),
            payload.get("timestamp"),
        )
    )

    frame_id         = _first_non_empty(record.get("frame_id"), payload.get("frame_id"))
    device_id        = _string_or_none(payload.get("device_id"))
    scene_type       = _string_or_none(payload.get("scene_type"))
    scene_name       = _string_or_none(payload.get("scene_name"))
    pedestrian_count = _coerce_int(payload.get("pedestrian_count"))

    emergency_level   = _string_or_none(emergency.get("level"))
    emergency_action  = _string_or_none(emergency.get("action"))
    emergency_message = _string_or_none(emergency.get("message"))

    gpu2_results   = payload.get("gpu2_results")
    gpu3_response  = payload.get("gpu3_response")
    final_decision = _first_non_empty(
        payload.get("final_decision"),
        payload.get("feature_outputs"),
        record.get("response_type"),
    )

    # --- Classify event type (now returns subtype as well) ---
    event_type, subtype, event_type_rule = _derive_event_type(
        record=record,
        payload=payload,
        emergency_level=emergency_level,
        emergency_action=emergency_action,
        emergency_message=emergency_message,
        pedestrian_count=pedestrian_count,
        scene_type=scene_type,
        scene_name=scene_name,
    )

    severity, severity_rule = _derive_severity(
        emergency_level=emergency_level,
        emergency_action=emergency_action,
        emergency_message=emergency_message,
        gpu2_results=gpu2_results,
        gpu3_response=gpu3_response,
        final_decision=final_decision,
    )

    lat = _coerce_float(
        _first_non_empty(
            payload.get("lat"),
            payload.get("latitude"),
            _deep_get(payload, "location", "lat"),
            _deep_get(payload, "location", "latitude"),
        )
    )
    lng = _coerce_float(
        _first_non_empty(
            payload.get("lng"),
            payload.get("lon"),
            payload.get("longitude"),
            _deep_get(payload, "location", "lng"),
            _deep_get(payload, "location", "lon"),
            _deep_get(payload, "location", "longitude"),
        )
    )

    metadata_json = {
        # ---- Required by metric_engine: drives wandering / wrong-turn / fall counts ----
        "subtype": subtype,

        # ---- MITRA pipeline provenance ----
        "mitra": {
            "original_response_type": record.get("response_type"),
            "mapped_category":        event_type.value,
            "mapping_rule":           event_type_rule,
        },

        # ---- Raw pipeline fields (preserved in full) ----
        "source": {
            "kind":        "responses_full_jsonl",
            "record_type": "mitra_pipeline_output",
        },
        "status":               record.get("status"),
        "response_type":        record.get("response_type"),
        "frame_id":             frame_id,
        "feature_ids_detected": record.get("feature_ids_detected"),
        "device_id":            device_id,
        "scene_type":           scene_type,
        "scene_name":           scene_name,
        "pedestrian_count":     pedestrian_count,
        "processing_time_ms":   payload.get("processing_time_ms"),
        "emergency": {
            "level":   emergency_level,
            "action":  emergency_action,
            "message": emergency_message,
        },
        "signals": {
            "feature_outputs": payload.get("feature_outputs"),
            "gpu2_results":    gpu2_results,
            "gpu3_response":   gpu3_response,
            "final_decision":  final_decision,
        },
        "mapping": {
            "event_type_rule": event_type_rule,
            "severity_rule":   severity_rule,
        },
        "original_payload": payload,
        "original_record":  dict(record),
    }

    return PipelineEventRow(
        patient_id=patient_id,
        event_type=event_type,
        timestamp=timestamp,
        severity=severity,
        lat=lat,
        lng=lng,
        metadata_json=metadata_json,
    )


# ---------------------------------------------------------------------------
# Public: bulk helpers
# ---------------------------------------------------------------------------

def map_pipeline_jsonl_file(
    path: str | Path,
    *,
    default_patient_id:  int | None              = None,
    device_patient_map:  Mapping[str, int] | None = None,
    patient_resolver:    PatientResolver | None   = None,
) -> list[PipelineEventRow]:
    return [
        map_pipeline_record_to_event_row(
            record,
            default_patient_id=default_patient_id,
            device_patient_map=device_patient_map,
            patient_resolver=patient_resolver,
        )
        for record in iter_pipeline_records(path)
    ]


def map_pipeline_jsonl_file_to_dicts(
    path: str | Path,
    *,
    default_patient_id:  int | None              = None,
    device_patient_map:  Mapping[str, int] | None = None,
    patient_resolver:    PatientResolver | None   = None,
) -> list[dict[str, Any]]:
    return [
        row.to_insert_dict()
        for row in map_pipeline_jsonl_file(
            path,
            default_patient_id=default_patient_id,
            device_patient_map=device_patient_map,
            patient_resolver=patient_resolver,
        )
    ]


def insert_pipeline_jsonl_events(
    db,
    path: str | Path,
    *,
    default_patient_id:  int | None              = None,
    device_patient_map:  Mapping[str, int] | None = None,
    patient_resolver:    PatientResolver | None   = None,
) -> list[Any]:
    rows   = map_pipeline_jsonl_file(
        path,
        default_patient_id=default_patient_id,
        device_patient_map=device_patient_map,
        patient_resolver=patient_resolver,
    )
    events = [row.to_event_model() for row in rows]
    db.add_all(events)
    db.commit()
    for event in events:
        db.refresh(event)
    return events


# ---------------------------------------------------------------------------
# Private: patient resolution
# ---------------------------------------------------------------------------

def _resolve_patient_id(
    record: Mapping[str, Any],
    payload: Mapping[str, Any],
    *,
    default_patient_id: int | None,
    device_patient_map: Mapping[str, int] | None,
    patient_resolver:   PatientResolver | None,
) -> int:
    if patient_resolver is not None:
        resolved = patient_resolver(record)
        if resolved is not None:
            return resolved

    device_id = _string_or_none(payload.get("device_id"))
    if device_id and device_patient_map:
        if device_id in device_patient_map:
            return device_patient_map[device_id]
        if str(device_id) in device_patient_map:
            return device_patient_map[str(device_id)]

    if default_patient_id is not None:
        return default_patient_id

    raise ValueError(
        "Could not resolve patient_id. Provide default_patient_id, "
        "device_patient_map, or patient_resolver."
    )


# ---------------------------------------------------------------------------
# Private: event type derivation
# Returns (EventType, subtype, rule_description).
# subtype is written into metadata_json and read by metric_engine.py.
# ---------------------------------------------------------------------------

def _derive_event_type(
    *,
    record:            Mapping[str, Any],
    payload:           Mapping[str, Any],
    emergency_level:   str | None,
    emergency_action:  str | None,
    emergency_message: str | None,
    pedestrian_count:  int | None,
    scene_type:        str | None,
    scene_name:        str | None,
) -> tuple[EventType, str, str]:
    """
    Map a pipeline record to (event_type, subtype, rule_description).

    Priority order
    ──────────────
    1. FALL / fall_detected        — emergency block present AND fall signal matched
    2. FALL / fall_detected        — confirmed fall keyword in signals (no emergency block)
    3. FALL / near_fall_detected   — fall keyword only; stored but NOT counted by metric engine
    4. WANDERING_EPISODE / wandering_episode_started — outdoor / boundary / lost signals
    5. WRONG_TURN / wrong_turn_detected              — navigation / route confusion signals
    6. AGITATION / emergency_button_pressed          — emergency block, no specific category
    7. AGITATION / pipeline_event                    — no matching signal; never affects metrics
    """
    signal_blob = _text_blob(
        record.get("response_type"),
        record.get("status"),
        scene_type,
        scene_name,
        emergency_level,
        emergency_action,
        emergency_message,
        payload.get("feature_outputs"),
        payload.get("gpu2_results"),
        payload.get("gpu3_response"),
    )

    has_emergency_block = bool(emergency_level or emergency_action or emergency_message)

    # 1. Emergency block + any fall signal → confirmed fall
    if has_emergency_block and (
        any(h in signal_blob for h in _FALL_CONFIRMED_HINTS)
        or any(h in signal_blob for h in _FALL_HINTS)
    ):
        return (
            EventType.FALL,
            "fall_detected",
            "emergency block + fall/safety signal",
        )

    # 2. Confirmed fall keyword without emergency block → still a confirmed fall
    if any(h in signal_blob for h in _FALL_CONFIRMED_HINTS):
        return (
            EventType.FALL,
            "fall_detected",
            "confirmed fall keyword (no emergency block)",
        )

    # 3. Softer fall keyword, no emergency → near-fall (visible in timeline, not counted)
    if any(h in signal_blob for h in _FALL_HINTS):
        return (
            EventType.FALL,
            "near_fall_detected",
            "fall keyword without emergency confirmation",
        )

    # 4. Outdoor / boundary / prolonged behaviour → wandering episode
    if any(h in signal_blob for h in _WANDERING_HINTS):
        return (
            EventType.WANDERING_EPISODE,
            "wandering_episode_started",
            "wandering/outdoor/boundary signal",
        )

    # 5. Navigation confusion / wrong direction → wrong turn
    if any(h in signal_blob for h in _WRONG_TURN_HINTS):
        return (
            EventType.WRONG_TURN,
            "wrong_turn_detected",
            "navigation error / route confusion signal",
        )

    # 6. Emergency block with no specific category (person triggered alert)
    if has_emergency_block:
        return (
            EventType.AGITATION,
            "emergency_button_pressed",
            "emergency block — no specific fall/wander/nav signal",
        )

    # 7. Default: generic pipeline record — stored for audit, does not affect any metric
    return (
        EventType.AGITATION,
        "pipeline_event",
        "no matching signal — generic pipeline record",
    )


# ---------------------------------------------------------------------------
# Private: severity derivation (unchanged)
# ---------------------------------------------------------------------------

def _derive_severity(
    *,
    emergency_level:   str | None,
    emergency_action:  str | None,
    emergency_message: str | None,
    gpu2_results:      Any,
    gpu3_response:     Any,
    final_decision:    Any,
) -> tuple[Severity, str]:
    normalized_level = (emergency_level or "").strip().lower()
    if normalized_level in _CRITICAL_LEVELS:
        return Severity.CRITICAL, f"emergency.level={normalized_level}"
    if normalized_level in _WARNING_LEVELS:
        return Severity.WARNING, f"emergency.level={normalized_level}"

    signal_blob = _text_blob(
        emergency_action,
        emergency_message,
        gpu2_results,
        gpu3_response,
        final_decision,
    )
    if any(hint in signal_blob for hint in _EMERGENCY_HINTS):
        return Severity.CRITICAL, "matched emergency keyword in action/message/signals"
    if any(hint in signal_blob for hint in _FALL_HINTS):
        return Severity.WARNING, "matched safety keyword in action/message/signals"

    return Severity.INFO, "no emergency signal found"


# ---------------------------------------------------------------------------
# Private: coercion helpers (unchanged)
# ---------------------------------------------------------------------------

def _coerce_timestamp(value: Any) -> datetime:
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    if value is None:
        raise ValueError("Pipeline record is missing ts/timestamp")

    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=UTC)

    text = str(value).strip()
    if not text:
        raise ValueError("Pipeline record has an empty ts/timestamp")

    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _deep_get(value: Any, *path: str) -> Any:
    current = value
    for key in path:
        if not isinstance(current, Mapping):
            return None
        current = current.get(key)
    return current


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _first_non_empty(*values: Any) -> Any:
    for value in values:
        if value is None:
            continue
        if isinstance(value, str) and not value.strip():
            continue
        return value
    return None


def _string_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _coerce_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    try:
        return int(str(value).strip())
    except (TypeError, ValueError):
        return None


def _coerce_float(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _text_blob(*parts: Any) -> str:
    values: list[str] = []
    for part in parts:
        if part is None:
            continue
        if isinstance(part, str):
            text = part.strip()
        else:
            text = json.dumps(part, sort_keys=True, default=str)
        if text:
            values.append(text.lower())
    return " | ".join(values)
