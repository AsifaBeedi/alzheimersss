# MITRA Alzheimer's & Dementia Monitoring Framework

## Executive Summary

This repository contains a working local demo of the MITRA monitoring system for Alzheimer's and dementia care.

The project currently consists of:

- A `FastAPI` backend in [backend/app/main.py](backend/app/main.py)
- A `React + Vite` frontend dashboard in [frontend/src/pages/Dashboard.jsx](frontend/src/pages/Dashboard.jsx)
- A local SQLite demo database at [backend/mitra_demo.db](backend/mitra_demo.db)

The demo is designed to simulate a wearable-based patient monitoring workflow:

1. Raw patient/device/event data is seeded or ingested.
2. Daily metrics are computed and stored.
3. Alert rules are evaluated from those stored metrics.
4. The frontend dashboard reads the prepared summary, trend, alert, and timeline data.

As of **April 17, 2026**, the dashboard summary issue reported during testing has been fixed. The main cause was that the dashboard summary endpoint existed in code but its router was not registered in the FastAPI application, so `GET /api/v1/patients/{id}/summary` returned `404`.

## Project Goal

The purpose of this system is to provide a clinician/caregiver-facing dashboard that can surface:

- patient movement behavior
- wandering episodes
- wrong-turn behavior
- device wear adherence
- fall events
- a composite independence score
- active alerts
- a chronological event timeline

The demo currently operates on synthetic data rather than live wearable streams.

## Current Functional Scope

### What is working

- Patient list and selection
- Demo data seeding
- Daily metric computation
- Alert generation
- Patient timeline retrieval
- Patient alerts retrieval
- Patient daily metric retrieval
- Patient dashboard summary retrieval
- Frontend rendering of overview cards, trend charts, alerts, and report preview

### What is partially implemented

- A second "clinical summary" subsystem exists, but is not finished
- Some service modules are placeholders with `NotImplementedError`
- There are duplicate summary-related modules, one active and one incomplete

### What is not yet complete

- Production-grade live ingestion flow
- Completed clinical summary persistence workflow
- Full event ingestion service layer implementation
- Alert acknowledgement/resolution workflow in UI
- Formal tests and deployment packaging

## High-Level Architecture

The backend follows a 3-layer model described in [backend/app/main.py](backend/app/main.py).

### Layer 1: Raw Data / Event Ingestion

This layer stores patient, location, wear-session, and event data.

Main entities:

- `Patient`
- `LocationPoint`
- `WearSession`
- `Event`

Relevant API groups:

- `/api/v1/patients`
- `/api/v1/location-points`
- `/api/v1/wear-sessions`
- `/api/v1/events`

### Layer 2: Daily Metric Engine

This layer computes one `DailyMetric` row per patient per date.

Implemented in:

- [backend/app/services/metric_engine.py](backend/app/services/metric_engine.py)
- [backend/app/jobs/daily_metrics.py](backend/app/jobs/daily_metrics.py)

Stored metrics:

- `wandering_episode_count`
- `wrong_turn_count`
- `movement_radius_m`
- `wear_hours`
- `fall_count`
- `independence_score`

### Layer 3: Summary and Alerts

This layer prepares dashboard-friendly output from stored daily metrics and alerts.

Implemented dashboard summary path:

- [backend/app/api/summaries.py](backend/app/api/summaries.py)
- [backend/app/services/summary_engine.py](backend/app/services/summary_engine.py)

Implemented alert path:

- [backend/app/services/alert_engine.py](backend/app/services/alert_engine.py)
- [backend/app/jobs/generate_alerts.py](backend/app/jobs/generate_alerts.py)

## How the Data Flow Works

### 1. Demo data is created

The seed logic lives in [backend/app/services/synthetic_data_generator.py](backend/app/services/synthetic_data_generator.py).

It creates:

- 2 demo patients
- 30 days of wear sessions
- GPS/location points
- wandering, wrong-turn, fall, and agitation events
- seeded `DailyMetric` rows for the demo dataset

The seeded patient profiles are:

- Margaret O'Brien, age 74
- Thomas Greenfield, age 81

Important detail:

- The synthetic generator uses a fixed base date of **March 17, 2026**
- It generates a 30-day window ending on **April 15, 2026**
- This means if the application is opened on later dates, the dashboard still uses the latest available stored metric data from that seeded range

### 2. Daily metrics are computed or recomputed

The batch job in [backend/app/jobs/daily_metrics.py](backend/app/jobs/daily_metrics.py) discovers all dates that have source data and writes or updates `DailyMetric` rows.

This is triggered through:

- `POST /api/v1/compute-metrics/`

The job is safe to run multiple times because it upserts existing rows.

### 3. Alerts are generated from stored metrics

The batch job in [backend/app/jobs/generate_alerts.py](backend/app/jobs/generate_alerts.py) reads each patient's stored daily metrics and evaluates alert rules.

This is triggered through:

- `POST /api/v1/generate-alerts/`

Alert rules currently implemented:

- Wandering frequency increase
- Movement radius decline
- Low wear adherence
- Confirmed fall detection
- Low independence score

Alerts are deduplicated by patient, rule, and metric date, so rerunning the job does not create duplicate open alerts for the same condition.

### 4. Dashboard summary is built from stored data

The dashboard does not recompute metrics on the fly. It reads:

- `DailyMetric` rows
- open `Alert` rows

and assembles:

- latest values for all six metrics
- 30-day trend arrays
- open alerts
- summary payload for the frontend

The active endpoint is:

- `GET /api/v1/patients/{patient_id}/summary`

This endpoint is implemented in [backend/app/api/summaries.py](backend/app/api/summaries.py).

## Frontend Behavior

The main dashboard page is [frontend/src/pages/Dashboard.jsx](frontend/src/pages/Dashboard.jsx).

On patient selection, the frontend requests:

- `/patients/{id}/summary`
- `/patients/{id}/daily-metrics`
- `/patients/{id}/alerts`
- `/patients/{id}/timeline`

The frontend also exposes three admin buttons:

- `Seed Demo Data`
- `Compute Metrics`
- `Generate Alerts`

These buttons call the backend utility endpoints and then refresh patient data in the UI.

## Root Cause of the Dashboard Issue

### Reported symptom

On **April 17, 2026**, the dashboard showed:

- alerts loading correctly
- timeline loading correctly
- daily metrics endpoint returning `200`
- summary endpoint returning `404`
- overview cards and charts displaying `No data`

Observed backend log pattern:

- `GET /api/v1/patients/1/summary HTTP/1.1" 404 Not Found`
- `GET /api/v1/patients/1/timeline ... 200 OK`
- `GET /api/v1/patients/1/daily-metrics ... 200 OK`
- `GET /api/v1/patients/1/alerts?status=open ... 200 OK`

### Actual cause

The summary endpoint implementation already existed in:

- [backend/app/api/summaries.py](backend/app/api/summaries.py)

However, its router was **not included** in:

- [backend/app/api/__init__.py](backend/app/api/__init__.py)

So the frontend was correctly calling the right URL, but FastAPI had never mounted that route.

### Fix applied on April 17, 2026

The summary router was registered in:

- [backend/app/api/__init__.py](backend/app/api/__init__.py)

Result after fix:

- `GET /api/v1/patients/1/summary` returns `200`
- latest values, trends, and alerts are returned in one summary payload
- dashboard cards and charts can render again

## Dependency Compatibility Issue Fixed

Another issue encountered on **April 17, 2026** was a backend install failure on `Python 3.13.5`.

### Symptom

`pip install -r requirements.txt` failed while building `pydantic-core`.

### Cause

The project had older dependency pins that were not compatible with Python 3.13 on Windows:

- `pydantic==2.7.1`
- `pydantic-settings==2.2.1`
- `sqlalchemy==2.0.30`

### Fix applied

The pins in [backend/requirements.txt](backend/requirements.txt) were updated to:

- `pydantic==2.13.1`
- `pydantic-settings==2.13.1`
- `sqlalchemy==2.0.49`

This was verified to work on:

- Python 3.12.7
- Python 3.13.5

## Important Code Paths

### Backend

- App entry point: [backend/app/main.py](backend/app/main.py)
- Router aggregation: [backend/app/api/__init__.py](backend/app/api/__init__.py)
- Dashboard summary API: [backend/app/api/summaries.py](backend/app/api/summaries.py)
- Incomplete legacy summary API: [backend/app/api/summary.py](backend/app/api/summary.py)
- Metric engine: [backend/app/services/metric_engine.py](backend/app/services/metric_engine.py)
- Summary engine: [backend/app/services/summary_engine.py](backend/app/services/summary_engine.py)
- Alert engine: [backend/app/services/alert_engine.py](backend/app/services/alert_engine.py)
- Synthetic demo data generator: [backend/app/services/synthetic_data_generator.py](backend/app/services/synthetic_data_generator.py)

### Frontend

- Root app: [frontend/src/App.jsx](frontend/src/App.jsx)
- Main dashboard page: [frontend/src/pages/Dashboard.jsx](frontend/src/pages/Dashboard.jsx)
- API client: [frontend/src/api/client.js](frontend/src/api/client.js)

## Current Known Gaps / Risks

The following areas are present in the codebase but not complete:

- [backend/app/services/summary_service.py](backend/app/services/summary_service.py) contains `NotImplementedError`
- [backend/app/jobs/summary_generate_job.py](backend/app/jobs/summary_generate_job.py) contains `NotImplementedError`
- [backend/app/api/summary.py](backend/app/api/summary.py) contains `NotImplementedError`
- [backend/app/services/event_service.py](backend/app/services/event_service.py) contains `NotImplementedError`
- [backend/app/services/alert_service.py](backend/app/services/alert_service.py) contains `NotImplementedError`

Important interpretation:

- The dashboard summary feature currently works through `summary_engine` plus `api/summaries.py`
- A separate "clinical summary" subsystem appears to be planned but is not completed
- This duplication can confuse maintainers unless consolidated later

## Local Run Instructions

### Backend

```powershell
cd C:\Users\Asifa Bandulal Beed\Downloads\alzheimers\backend
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

Backend URLs:

- API base: `http://localhost:8000/api/v1`
- Swagger UI: `http://localhost:8000/docs`
- Health check: `http://localhost:8000/health`

### Frontend

```powershell
cd C:\Users\Asifa Bandulal Beed\Downloads\alzheimers\frontend
npm install
npm run dev
```

The frontend expects the backend at:

- `http://localhost:8000/api/v1`

The backend CORS config currently allows:

- `http://localhost:5173`

## Recommended Demo Sequence

For a fresh or reset local database:

1. Start the backend.
2. Open `http://localhost:8000/docs`.
3. Call `POST /api/v1/seed-demo-data/`.
4. Call `POST /api/v1/compute-metrics/`.
5. Call `POST /api/v1/generate-alerts/`.
6. Start the frontend.
7. Open the dashboard and select a patient.

If the database already contains demo patients, the seed step is intentionally skipped.

## What the Dashboard Should Show After the Fix

For patient `1` with the current demo dataset, the summary endpoint now returns:

- latest independence score
- latest wandering count
- latest wrong-turn count
- latest movement radius
- latest wear hours
- latest fall count
- open alerts
- 30-day trends for all six metrics

This means:

- the overview cards should populate
- the trend charts should render lines
- the alerts panel should list open alerts
- the report preview can use the same summary payload

## Recommended Next Steps for Supervisor Review

### Immediate next steps

- Decide whether this repository remains a demo/prototype or should move toward production hardening
- Consolidate the duplicate summary modules into one clear summary architecture
- Remove or complete unfinished placeholder services
- Add basic backend test coverage for summary, metric, and alert endpoints
- Add a database reset script or documented reset workflow for repeated demo runs

### If continuing development

- Finalize live ingestion flow from wearable or sensor source
- Move from SQLite demo storage to PostgreSQL for multi-user or production use
- Add authentication and role-based access if external users will access the dashboard
- Implement clinician alert acknowledgement and resolution workflows
- Add audit logging and formal API contracts

## Bottom Line

The system is currently best described as a **working local demo / prototype** with a functioning patient dashboard, seeded data pipeline, metric engine, and alert engine.

It is not yet a fully completed production platform, but it is now in a stable enough state for:

- demo presentation
- architecture review
- feature planning
- supervisor sign-off on next development steps

The two concrete fixes completed on **April 17, 2026** were:

1. Python dependency upgrades so backend installation works on modern Python versions.
2. Registration of the dashboard summary router so the frontend can load summary data correctly.
