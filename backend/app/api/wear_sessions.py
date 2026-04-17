from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.patient import Patient
from app.models.wear_session import WearSession
from app.schemas.wear_session import WearSessionCreate, WearSessionRead

router = APIRouter()


@router.post("/", response_model=WearSessionRead, status_code=201)
def create_wear_session(body: WearSessionCreate, db: Session = Depends(get_db)):
    if db.get(Patient, body.patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient {body.patient_id} not found")

    session = WearSession(**body.model_dump())
    db.add(session)
    db.commit()
    db.refresh(session)
    return session
