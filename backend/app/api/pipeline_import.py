from pathlib import Path
import tempfile

from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.services.pipeline_event_mapper import (
    insert_pipeline_jsonl_events,
    map_pipeline_jsonl_file_to_dicts,
)

router = APIRouter()


class PipelineImportRequest(BaseModel):
    file_path: str = Field(
        default="C:/Users/Asifa Bandulal Beed/Downloads/responses_full.jsonl"
    )
    default_patient_id: int | None = None
    device_patient_map: dict[str, int] = Field(default_factory=dict)
    dry_run: bool = False


class PipelineImportResult(BaseModel):
    file_path: str
    dry_run: bool
    rows_read: int
    events_created: int


@router.post("/", response_model=PipelineImportResult, status_code=200)
def import_pipeline_events(
    body: PipelineImportRequest,
    db: Session = Depends(get_db),
):
    if body.default_patient_id is None and not body.device_patient_map:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide default_patient_id or device_patient_map so the importer "
                "can resolve patient_id for each record."
            ),
        )

    try:
        if body.dry_run:
            rows = map_pipeline_jsonl_file_to_dicts(
                body.file_path,
                default_patient_id=body.default_patient_id,
                device_patient_map=body.device_patient_map,
            )
            return PipelineImportResult(
                file_path=body.file_path,
                dry_run=True,
                rows_read=len(rows),
                events_created=0,
            )

        events = insert_pipeline_jsonl_events(
            db,
            body.file_path,
            default_patient_id=body.default_patient_id,
            device_patient_map=body.device_patient_map,
        )
        return PipelineImportResult(
            file_path=body.file_path,
            dry_run=False,
            rows_read=len(events),
            events_created=len(events),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/upload", response_model=PipelineImportResult, status_code=200)
async def import_pipeline_events_upload(
    file: UploadFile = File(...),
    default_patient_id: int | None = Form(default=None),
    device_patient_map_json: str | None = Form(default=None),
    dry_run: bool = Form(default=False),
    db: Session = Depends(get_db),
):
    if default_patient_id is None and not device_patient_map_json:
        raise HTTPException(
            status_code=400,
            detail=(
                "Provide default_patient_id or device_patient_map_json so the importer "
                "can resolve patient_id for each record."
            ),
        )

    device_patient_map: dict[str, int] = {}
    if device_patient_map_json:
        try:
            import json

            parsed = json.loads(device_patient_map_json)
            if not isinstance(parsed, dict):
                raise ValueError("device_patient_map_json must decode to an object")
            device_patient_map = {str(k): int(v) for k, v in parsed.items()}
        except Exception as exc:
            raise HTTPException(
                status_code=400,
                detail="device_patient_map_json must be valid JSON like {\"device-1\": 1}",
            ) from exc

    suffix = Path(file.filename or "responses_full").suffix or ".jsonl"
    temp_path: str | None = None

    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_path = temp_file.name

        if dry_run:
            rows = map_pipeline_jsonl_file_to_dicts(
                temp_path,
                default_patient_id=default_patient_id,
                device_patient_map=device_patient_map,
            )
            return PipelineImportResult(
                file_path=file.filename or temp_path,
                dry_run=True,
                rows_read=len(rows),
                events_created=0,
            )

        events = insert_pipeline_jsonl_events(
            db,
            temp_path,
            default_patient_id=default_patient_id,
            device_patient_map=device_patient_map,
        )
        return PipelineImportResult(
            file_path=file.filename or temp_path,
            dry_run=False,
            rows_read=len(events),
            events_created=len(events),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if temp_path:
            try:
                Path(temp_path).unlink(missing_ok=True)
            except OSError:
                pass
