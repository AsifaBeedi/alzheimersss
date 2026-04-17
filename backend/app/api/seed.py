from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.patient import Patient
from app.models.location_point import LocationPoint
from app.models.wear_session import WearSession
from app.models.event import Event
from app.services.synthetic_data_generator import seed_demo_data

router = APIRouter()


class SeedResult(BaseModel):
    seeded: bool            # True = data was just inserted; False = already existed
    message: str
    patients: int
    location_points: int
    wear_sessions: int
    events: int


@router.post("/", response_model=SeedResult)
def run_seed(response: Response, db: Session = Depends(get_db)):
    """
    Populate the database with synthetic demo data for 2 patients × 30 days.
    Safe to call repeatedly — does nothing if demo patients already exist.
    Returns current record counts regardless of whether seeding ran.
    """
    already_existed = db.query(Patient).count() > 0

    seed_demo_data(db)      # no-op when patients exist

    patients        = db.query(Patient).count()
    location_points = db.query(LocationPoint).count()
    wear_sessions   = db.query(WearSession).count()
    events          = db.query(Event).count()

    if already_existed:
        response.status_code = 200
        message = "Demo data already present — no changes made."
    else:
        response.status_code = 201
        message = (
            f"Seeded {patients} patients with 30 days of synthetic data "
            f"({events} events, {location_points} location points)."
        )

    return SeedResult(
        seeded=not already_existed,
        message=message,
        patients=patients,
        location_points=location_points,
        wear_sessions=wear_sessions,
        events=events,
    )
