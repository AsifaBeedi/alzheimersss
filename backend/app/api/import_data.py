"""
Pipeline Data Import API — fixed-path single-endpoint importer.

POST /api/v1/import-pipeline-data
    Read backend/data/responses_full.jsonl and insert the mapped events into
    the Event table for the given patient.

    This is a convenience wrapper around insert_pipeline_jsonl_events for
    demo and Render deployments where the JSONL file lives at a known path
    inside the project.  No file-path parameter is accepted — the path is
    resolved relative to this module so it works in every environment.
"""

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.pipeline_event_mapper import insert_pipeline_jsonl_events

router = APIRouter()

# Resolved once at import time.
# backend/app/api/import_data.py  → .parent × 3 → backend/
# Then down into data/responses_full.jsonl
_DATA_FILE: Path = (
    Path(__file__).resolve().parent.parent.parent / "data" / "responses_full.jsonl"
)


class ImportResult(BaseModel):
    file_path:         str
    records_processed: int
    events_inserted:   int


@router.post("/", response_model=ImportResult, status_code=200)
def import_pipeline_data(
    patient_id: int = Query(
        default=1,
        ge=1,
        description="Patient ID to assign all imported events to.",
    ),
    db: Session = Depends(get_db),
):
    """
    Import MITRA pipeline events from the bundled JSONL file.

    Reads **backend/data/responses_full.jsonl**, maps every record to one of
    the four metric-driving event types (WANDERING_EPISODE, WRONG_TURN, FALL,
    AGITATION), and inserts them into the Event table for `patient_id`.

    After a successful import, run:
      POST /api/v1/compute-metrics   — recompute DailyMetric rows
      POST /api/v1/generate-alerts   — evaluate updated metrics for alerts

    Note: this endpoint does not deduplicate — calling it twice inserts the
    records twice.  Wipe and reseed the database if a clean state is needed.
    """
    if not _DATA_FILE.exists():
        raise HTTPException(
            status_code=404,
            detail=(
                f"Data file not found at {_DATA_FILE}. "
                "Ensure backend/data/responses_full.jsonl is committed to the repo."
            ),
        )

    try:
        events = insert_pipeline_jsonl_events(
            db,
            _DATA_FILE,
            default_patient_id=patient_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Import failed: {exc}") from exc

    return ImportResult(
        file_path=str(_DATA_FILE),
        records_processed=len(events),
        events_inserted=len(events),
    )
