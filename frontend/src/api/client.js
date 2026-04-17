/**
 * MITRA API client.
 * Uses VITE_API_BASE_URL when set; otherwise falls back to local dev.
 *
 * Each function returns the parsed JSON body directly, or throws on non-2xx.
 */

import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:8000/api/v1";

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: { "Content-Type": "application/json" },
});

// Unwrap .data on every response so callers just get the payload.
const get  = (path, params) => api.get(path, { params }).then(r => r.data);
const post = (path, body)   => api.post(path, body).then(r => r.data);


// ---------------------------------------------------------------------------
// Patients
// ---------------------------------------------------------------------------

/** GET /patients — list all patients */
export const getPatients = () =>
  get("/patients");

/** GET /patients/:id — single patient */
export const getPatient = (id) =>
  get(`/patients/${id}`);


// ---------------------------------------------------------------------------
// Computed data — patient-scoped
// ---------------------------------------------------------------------------

/**
 * GET /patients/:id/daily-metrics
 * @param {Object} [params]
 * @param {string} [params.from_date]  ISO date string, e.g. "2026-03-17"
 * @param {string} [params.to_date]   ISO date string
 */
export const getDailyMetrics = (id, params = {}) =>
  get(`/patients/${id}/daily-metrics`, params);

/** GET /patients/:id/latest-metrics — single most-recent DailyMetric row */
export const getLatestMetrics = (id) =>
  get(`/patients/${id}/latest-metrics`);

/**
 * GET /patients/:id/summary — 30-day snapshot with latest values, trends, alerts.
 * @param {string} [asOfDate]  ISO date string
 */
export const getSummary = (id, asOfDate) =>
  get(`/patients/${id}/summary`, asOfDate ? { as_of_date: asOfDate } : undefined);

/**
 * GET /patients/:id/alerts
 * @param {string} [status]  "open" | "acknowledged" | "resolved" (omit for all)
 * @param {number} [limit]
 */
export const getAlerts = (id, status, limit) =>
  get(`/patients/${id}/alerts`, {
    ...(status ? { status } : {}),
    ...(limit  ? { limit  } : {}),
  });

/**
 * GET /patients/:id/timeline — chronological events.
 * @param {Object} [params]
 * @param {string} [params.from_date]
 * @param {string} [params.to_date]
 * @param {number} [params.limit]
 */
export const getTimeline = (id, params = {}) =>
  get(`/patients/${id}/timeline`, params);


// ---------------------------------------------------------------------------
// Admin / utility
// ---------------------------------------------------------------------------

/** POST /seed-demo-data/ — populate synthetic data (idempotent) */
export const seedDemoData = () =>
  post("/seed-demo-data/");

/** POST /compute-metrics/ — compute DailyMetric rows for all patients */
export const computeMetrics = () =>
  post("/compute-metrics/");

/** POST /generate-alerts/ — evaluate alert rules for all patients */
export const generateAlerts = () =>
  post("/generate-alerts/");
