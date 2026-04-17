from fastapi import APIRouter

# --- Raw data ingestion routers ------------------------------------------
from app.api.patients import router as patients_router
from app.api.location_points import router as location_points_router
from app.api.wear_sessions import router as wear_sessions_router
from app.api.events import router as events_router

# --- Patient-scoped computed-data routers ---------------------------------
from app.api.metrics import router as metrics_router
from app.api.alerts import router as alerts_router
from app.api.timeline import router as timeline_router
from app.api.summaries import router as summaries_router
from app.api.pipeline_import import router as pipeline_import_router

# --- Utilities -----------------------------------------------------------
from app.api.seed import router as seed_router

router = APIRouter()

# Patient CRUD + raw sub-resources (location-points, wear-sessions, events)
router.include_router(patients_router,        prefix="/patients",        tags=["Patients"])
router.include_router(location_points_router, prefix="/location-points", tags=["Location Points"])
router.include_router(wear_sessions_router,   prefix="/wear-sessions",   tags=["Wear Sessions"])
router.include_router(events_router,          prefix="/events",          tags=["Events"])

# Computed data — all mounted under /patients so URLs are:
#   GET /api/v1/patients/{id}/daily-metrics
#   GET /api/v1/patients/{id}/latest-metrics
#   GET /api/v1/patients/{id}/alerts
#   GET /api/v1/patients/{id}/summary
#   GET /api/v1/patients/{id}/timeline
router.include_router(metrics_router,   prefix="/patients", tags=["Metrics"])
router.include_router(alerts_router,    prefix="/patients", tags=["Alerts"])
router.include_router(timeline_router,  prefix="/patients", tags=["Timeline"])
router.include_router(summaries_router, prefix="/patients", tags=["Summary"])
router.include_router(
    pipeline_import_router,
    prefix="/import-pipeline-events",
    tags=["Pipeline Import"],
)

# Demo seed
router.include_router(seed_router, prefix="/seed-demo-data", tags=["Demo Seed"])
