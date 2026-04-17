import logging

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from app.core.config import settings

logger = logging.getLogger(__name__)

# SQLite requires check_same_thread=False when the same connection is shared
# across the FastAPI request thread pool. Safe here because SQLAlchemy's
# connection pool already serialises access per connection.
_connect_args = {"check_same_thread": False} if settings.DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    settings.DATABASE_URL,
    connect_args=_connect_args,
    echo=settings.DATABASE_ECHO,
)

# Enable WAL mode for SQLite — allows concurrent reads during a write,
# which matters once the seed job and the API run at the same time.
if settings.DATABASE_URL.startswith("sqlite"):
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------

def get_db():
    """Yield a SQLAlchemy session; always close it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Table creation
# ---------------------------------------------------------------------------

def init_db() -> None:
    """
    Create all tables that are registered on Base.metadata.

    Called once at application startup. Safe to call on every restart —
    create_all is a no-op for tables that already exist.

    Models must be imported before this function is called so SQLAlchemy
    knows about them. The import is done here to keep the call site clean.
    """
    import app.models  # noqa: F401 — registers all ORM models on Base.metadata

    logger.info("Creating database tables (if not exist) at: %s", settings.DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    _normalize_legacy_enum_values()
    logger.info("Database ready.")


def _normalize_legacy_enum_values() -> None:
    """
    Normalize legacy enum strings already stored in SQLite.

    Earlier versions of the app wrote enum *names* such as `WRONG_TURN` and
    `LOW_INDEPENDENCE`, while the current ORM expects enum *values* such as
    `wrong_turn` and `low_independence`. If we do not normalize those rows,
    SQLAlchemy raises LookupError while reading timeline, alerts, and summary
    queries.

    This normalization is idempotent and safe to run at startup.
    """
    enum_updates = {
        "events": {
            "event_type": {
                "WANDERING_EPISODE": "wandering_episode",
                "WRONG_TURN": "wrong_turn",
                "FALL": "fall",
                "AGITATION": "agitation",
                "SAFETY_EVENT": "safety_event",
                "EMERGENCY_EVENT": "emergency_event",
                "SCENE_EVENT": "scene_event",
                "PEDESTRIAN_EVENT": "pedestrian_event",
                "PIPELINE_EVENT": "pipeline_event",
            },
            "severity": {
                "INFO": "info",
                "WARNING": "warning",
                "CRITICAL": "critical",
            },
        },
        "alerts": {
            "alert_type": {
                "WANDERING": "wandering",
                "LOW_ADHERENCE": "low_adherence",
                "LOW_INDEPENDENCE": "low_independence",
                "FALL": "fall",
            },
            "severity": {
                "INFO": "info",
                "WARNING": "warning",
                "CRITICAL": "critical",
            },
            "status": {
                "OPEN": "open",
                "ACKNOWLEDGED": "acknowledged",
                "RESOLVED": "resolved",
            },
        },
    }

    with engine.begin() as conn:
        for table_name, columns in enum_updates.items():
            for column_name, mapping in columns.items():
                for old_value, new_value in mapping.items():
                    conn.execute(
                        text(
                            f"UPDATE {table_name} "
                            f"SET {column_name} = :new_value "
                            f"WHERE {column_name} = :old_value"
                        ),
                        {"old_value": old_value, "new_value": new_value},
                    )
