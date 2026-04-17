from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.services.synthetic_data_generator import seed_demo_data


def run_seed() -> None:
    """Entry point for the seed job — opens its own session and delegates."""
    db: Session = SessionLocal()
    try:
        seed_demo_data(db)
    finally:
        db.close()
