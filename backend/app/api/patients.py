from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.patient import Patient
from app.models.location_point import LocationPoint
from app.models.wear_session import WearSession
from app.models.event import Event
from app.schemas.patient import PatientCreate, PatientUpdate, PatientRead
from app.schemas.location_point import LocationPointRead
from app.schemas.wear_session import WearSessionRead
from app.schemas.event import EventRead

router = APIRouter()


def _get_patient_or_404(patient_id: int, db: Session) -> Patient:
    patient = db.get(Patient, patient_id)
    if patient is None:
        raise HTTPException(status_code=404, detail=f"Patient {patient_id} not found")
    return patient


# ---------------------------------------------------------------------------
# Patient CRUD
# ---------------------------------------------------------------------------

@router.post("/", response_model=PatientRead, status_code=201)
def create_patient(body: PatientCreate, db: Session = Depends(get_db)):
    patient = Patient(**body.model_dump())
    db.add(patient)
    db.commit()
    db.refresh(patient)
    return patient


@router.get("/", response_model=list[PatientRead])
def list_patients(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    return db.query(Patient).order_by(Patient.id).offset(offset).limit(limit).all()


@router.get("/{patient_id}", response_model=PatientRead)
def get_patient(patient_id: int, db: Session = Depends(get_db)):
    return _get_patient_or_404(patient_id, db)


@router.patch("/{patient_id}", response_model=PatientRead)
def update_patient(patient_id: int, body: PatientUpdate, db: Session = Depends(get_db)):
    patient = _get_patient_or_404(patient_id, db)
    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(patient, field, value)
    db.commit()
    db.refresh(patient)
    return patient


# ---------------------------------------------------------------------------
# Patient-scoped list endpoints
# ---------------------------------------------------------------------------

@router.get("/{patient_id}/location-points", response_model=list[LocationPointRead])
def list_location_points(
    patient_id: int,
    limit: int = Query(200, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    _get_patient_or_404(patient_id, db)
    return (
        db.query(LocationPoint)
        .filter(LocationPoint.patient_id == patient_id)
        .order_by(LocationPoint.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{patient_id}/wear-sessions", response_model=list[WearSessionRead])
def list_wear_sessions(
    patient_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    _get_patient_or_404(patient_id, db)
    return (
        db.query(WearSession)
        .filter(WearSession.patient_id == patient_id)
        .order_by(WearSession.start_time.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )


@router.get("/{patient_id}/events", response_model=list[EventRead])
def list_events(
    patient_id: int,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
):
    _get_patient_or_404(patient_id, db)
    return (
        db.query(Event)
        .filter(Event.patient_id == patient_id)
        .order_by(Event.timestamp.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
