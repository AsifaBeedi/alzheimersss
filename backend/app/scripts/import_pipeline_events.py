from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.core.database import SessionLocal
from app.models.event import Event
from app.models.enums import EventType, Severity


_CRITICAL_LEVELS = {"critical", "high", "severe", "emergency"}
_WARNING_LEVELS = {"warning", "warn", "medium", "moderate", "elevated"}


def import_pipeline_events(
    jsonl_path: str | Path,
    *,
    default_patient_id: int,
    device_patient_map: dict[str, int] | None = None,
) -> int:
    """
    Read responses_full.jsonl line by line and insert mapped Event rows.

    Returns the number of created events.
    """
    path = Path(jsonl_path)
    created = 0
    device_patient_map = device_patient_map or {}

    db = SessionLocal()
    try:
        with path.open("r", encoding="utf-8") as handle:
            for line_number, raw_line in enumerate(handle, start=1):
                line = raw_line.strip()
                if not line:
                    continue

                record = json.loads(line)
                payload = _as_dict(record.get("payload"))
                emergency = _as_dict(payload.get("emergency"))

                patient_id = _resolve_patient_id(
                    payload=payload,
                    default_patient_id=default_patient_id,
                    device_patient_map=device_patient_map,
                )

                event = Event(
                    patient_id=patient_id,
                    event_type=_derive_event_type(payload),
                    timestamp=_coerce_timestamp(record.get("ts")),
                    severity=_derive_severity(emergency.get("level")),
                    lat=None,
                    lng=None,
                    metadata_json={
                        "source": "responses_full.jsonl",
                        "frame_id": record.get("frame_id") or payload.get("frame_id"),
                        "device_id": payload.get("device_id"),
                        "scene_type": payload.get("scene_type"),
                        "scene_name": payload.get("scene_name"),
                        "pedestrian_count": payload.get("pedestrian_count"),
                        "emergency": emergency,
                        "full_payload": payload,
                        "raw_record": record,
                        "line_number": line_number,
                    },
                )
                db.add(event)
                created += 1

        db.commit()
        return created
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def _resolve_patient_id(
    *,
    payload: dict[str, Any],
    default_patient_id: int,
    device_patient_map: dict[str, int],
) -> int:
    device_id = payload.get("device_id")
    if device_id is not None:
        mapped = device_patient_map.get(str(device_id))
        if mapped is not None:
            return mapped
    return default_patient_id


def _derive_event_type(payload: dict[str, Any]) -> EventType:
    emergency = _as_dict(payload.get("emergency"))
    if emergency.get("level"):
        return EventType.EMERGENCY_EVENT

    pedestrian_count = payload.get("pedestrian_count")
    if isinstance(pedestrian_count, (int, float)) and pedestrian_count > 0:
        return EventType.PEDESTRIAN_EVENT

    if payload.get("scene_type") or payload.get("scene_name"):
        return EventType.SCENE_EVENT

    return EventType.PIPELINE_EVENT


def _derive_severity(level: Any) -> Severity:
    normalized = str(level or "").strip().lower()
    if normalized in _CRITICAL_LEVELS:
        return Severity.CRITICAL
    if normalized in _WARNING_LEVELS:
        return Severity.WARNING
    return Severity.INFO


def _coerce_timestamp(value: Any) -> datetime:
    if value is None:
        raise ValueError("Missing ts field in pipeline record")

    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=UTC)

    if isinstance(value, (int, float)):
        seconds = value / 1000 if value > 10_000_000_000 else value
        return datetime.fromtimestamp(seconds, tz=UTC)

    text = str(value).strip()
    if text.endswith("Z"):
        text = text[:-1] + "+00:00"

    parsed = datetime.fromisoformat(text)
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=UTC)


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


if __name__ == "__main__":
    inserted = import_pipeline_events(
        "C:/Users/Asifa Bandulal Beed/Downloads/responses_full.jsonl",
        default_patient_id=1,
    )
    print(f"Inserted {inserted} events.")
