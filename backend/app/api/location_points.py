from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.patient import Patient
from app.models.location_point import LocationPoint
from app.schemas.location_point import LocationPointCreate, LocationPointRead

router = APIRouter()


@router.post("/", response_model=LocationPointRead, status_code=201)
def create_location_point(body: LocationPointCreate, db: Session = Depends(get_db)):
    if db.get(Patient, body.patient_id) is None:
        raise HTTPException(status_code=404, detail=f"Patient {body.patient_id} not found")

    point = LocationPoint(**body.model_dump())
    db.add(point)
    db.commit()
    db.refresh(point)
    return point
