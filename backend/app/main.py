"""
MITRA — Alzheimer's & Dementia Monitoring Framework
FastAPI application entry point.

3-Layer architecture:
  Layer 1  Event ingestion        POST /api/v1/events
  Layer 2  Metric Engine          GET  /api/v1/patients/{id}/daily-metrics
                                  GET  /api/v1/patients/{id}/latest-metrics
  Layer 3  Summary & Alerts       GET  /api/v1/patients/{id}/summary
                                  GET  /api/v1/patients/{id}/alerts
                                  GET  /api/v1/patients/{id}/timeline

Patient CRUD:       GET/POST/PATCH /api/v1/patients
Demo seed:          POST /api/v1/seed-demo-data
Metric compute:     POST /api/v1/compute-metrics
Pipeline import:    POST /api/v1/import-pipeline-data

Typical startup sequence (fresh database):
  1. POST /api/v1/seed-demo-data     — populate synthetic data
  2. POST /api/v1/compute-metrics    — compute and store DailyMetric rows
  3. POST /api/v1/generate-alerts    — evaluate thresholds, write Alert rows
  4. GET  /api/v1/patients           — list patients
  5. GET  /api/v1/patients/1/summary — dashboard payload

Run locally:
  cd backend
  uvicorn app.main:app --reload --port 8000
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Lifespan — startup / shutdown
# ---------------------------------------------------------------------------

@asynccontextmanager
async def lifespan(_app: FastAPI):
    logger.info("Starting MITRA API…")
    init_db()
    yield
    logger.info("MITRA API shut down.")


# ---------------------------------------------------------------------------
# App
# ---------------------------------------------------------------------------

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Alzheimer's & Dementia Monitoring Framework — iHelp Robotics",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# Health check — always available, no DB dependency
# ---------------------------------------------------------------------------

@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "ok", "service": settings.PROJECT_NAME}


# ---------------------------------------------------------------------------
# API routers
# ---------------------------------------------------------------------------

from app.api import router as api_router
app.include_router(api_router, prefix=settings.API_V1_PREFIX)

# ---------------------------------------------------------------------------
# Admin / utility routers — registered directly here for visibility
# ---------------------------------------------------------------------------

from app.api.summary import router as summary_router
app.include_router(
    summary_router,
    prefix=f"{settings.API_V1_PREFIX}/patients",
    tags=["Summary"],
)

from app.api.metrics_admin import router as metrics_admin_router
app.include_router(
    metrics_admin_router,
    prefix=f"{settings.API_V1_PREFIX}/compute-metrics",
    tags=["Metrics Admin"],
)

from app.api.alerts_admin import router as alerts_admin_router
app.include_router(
    alerts_admin_router,
    prefix=f"{settings.API_V1_PREFIX}/generate-alerts",
    tags=["Alerts Admin"],
)

from app.api.import_data import router as import_data_router
app.include_router(
    import_data_router,
    prefix=f"{settings.API_V1_PREFIX}/import-pipeline-data",
    tags=["Pipeline Import"],
)
