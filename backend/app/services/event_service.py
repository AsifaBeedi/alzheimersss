"""
Layer 1 — Event Engine service.
Validates inbound sensor events, computes spatial context, and persists to DB.
"""

from sqlalchemy.orm import Session


class EventService:
    def __init__(self, db: Session):
        self.db = db

    def ingest(self, payload: dict):
        """
        Accept a raw event payload, enrich it (distance_from_home, severity),
        write to the events table, and return the persisted Event.
        TODO: implement
        """
        raise NotImplementedError
