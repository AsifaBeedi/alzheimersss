from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.patient import Patient
from app.models.event import Event
from app.schemas.event import EventCreate, EventRead

router = APIRouter()


@router.post("/", response_model=EventRead, status_code=201)
def create_event(body: EventCreate, db: Session = Depends(get_db)):
    if db.get(Patient, body.patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient {body.patient_id} not found")

    event = Event(**body.model_dump())
    db.add(event)
    db.commit()
    db.refresh(event)
    return event
