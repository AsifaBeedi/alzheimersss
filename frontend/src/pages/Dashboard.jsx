/**
 * Dashboard — MITRA root page.
 *
 * Owns all data-fetching state and composes the six display components.
 * Admin action buttons (Seed / Compute / Generate) drive the backend
 * pipeline and reload patient data on completion.
 *
 * Layout (rows inside the Layout shell):
 *   [0] Admin action strip
 *   [1] OverviewCards          — 6 latest metric tiles
 *   [2] TrendCharts | AlertsPanel
 *   [3] ClinicalSummary | EventTimeline
 */

import { useState, useEffect } from "react";

import Layout          from "../components/Layout.jsx";
import OverviewCards   from "../components/OverviewCards.jsx";
import TrendCharts     from "../components/TrendCharts.jsx";
import AlertsPanel     from "../components/AlertsPanel.jsx";
import EventTimeline   from "../components/EventTimeline.jsx";
import ClinicalSummary from "../components/ClinicalSummary.jsx";
import ReportPreview   from "../components/ReportPreview.jsx";

import {
  getPatients,
  getSummary,
  getDailyMetrics,
  getAlerts,
  getTimeline,
  seedDemoData,
  computeMetrics,
  generateAlerts,
} from "../api/client.js";

// ── Data source note ──────────────────────────────────────────────────────────
// Renders a single unobtrusive line that labels which metrics come from the
// MITRA pipeline and which still rely on simulated support data.

function DataSourceNote({ sources }) {
  if (!sources) return null;

  const isPipeline = sources.events === "pipeline_jsonl";
  const radiusSim  = sources.movement_radius === "synthetic";
  const wearSim    = sources.wear_adherence  === "synthetic";

  // Nothing interesting to show in a fully synthetic or fully live scenario
  if (!isPipeline && !radiusSim && !wearSim) return null;

  return (
    <div className="flex flex-wrap items-center gap-x-5 gap-y-1 text-xs text-gray-600
                    border border-gray-800/50 rounded-lg px-4 py-2 bg-gray-900/40">
      <span className="text-gray-700 font-medium shrink-0">Data sources</span>

      {isPipeline && (
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-teal-500/60 shrink-0" />
          <span>
            Event insights&thinsp;—&thinsp;MITRA pipeline&thinsp;
            <span className="text-gray-700">(wandering · falls · wrong turns)</span>
          </span>
        </span>
      )}

      {(radiusSim || wearSim) && (
        <span className="flex items-center gap-1.5">
          <span className="w-1.5 h-1.5 rounded-full bg-gray-600 shrink-0" />
          <span>
            Simulated support data&thinsp;—&thinsp;
            <span className="text-gray-700">
              {[radiusSim && "movement radius", wearSim && "wear adherence"]
                .filter(Boolean)
                .join(" · ")}
            </span>
          </span>
        </span>
      )}
    </div>
  );
}

// ── Admin action definitions ──────────────────────────────────────────────────

const ADMIN_ACTIONS = [
  { key: "seed",    label: "Seed Demo Data",  fn: seedDemoData   },
  { key: "metrics", label: "Compute Metrics", fn: computeMetrics },
  { key: "alerts",  label: "Generate Alerts", fn: generateAlerts },
];

// ── Admin strip ───────────────────────────────────────────────────────────────

function AdminStrip({ running, status, onRun }) {
  return (
    <div className="flex items-center gap-2 flex-wrap">
      {ADMIN_ACTIONS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onRun(key)}
          disabled={running !== null}
          className="text-xs px-3 py-1.5 rounded border border-gray-800 text-gray-500
                     hover:border-gray-600 hover:text-gray-300
                     disabled:opacity-40 disabled:cursor-not-allowed
                     transition-colors"
        >
          {running === key ? "Running…" : label}
        </button>
      ))}

      {/* Inline status message */}
      {status && (
        <span
          className={`text-xs flex items-center gap-1.5 ml-1 ${
            status.ok ? "text-green-400" : "text-red-400"
          }`}
        >
          <span className={`w-1.5 h-1.5 rounded-full ${status.ok ? "bg-green-400" : "bg-red-400"}`} />
          {status.text}
        </span>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Dashboard() {

  // ── Patient list ─────────────────────────────────────────────────────────
  const [patients,        setPatients]        = useState([]);
  const [selectedId,      setSelectedId]      = useState(null);
  const [loadingPatients, setLoadingPatients] = useState(true);

  // ── Per-patient data ──────────────────────────────────────────────────────
  const [summary,       setSummary]       = useState(null);
  const [dailyMetrics,  setDailyMetrics]  = useState([]);
  const [alerts,        setAlerts]        = useState([]);
  const [events,        setEvents]        = useState([]);

  // Start as true so skeletons show during the initial patient-list fetch,
  // before selectedId is known and the per-patient effect fires.
  const [loadingSummary, setLoadingSummary] = useState(true);
  const [loadingMetrics, setLoadingMetrics] = useState(true);
  const [loadingAlerts,  setLoadingAlerts]  = useState(true);
  const [loadingEvents,  setLoadingEvents]  = useState(true);

  // ── Admin action state ────────────────────────────────────────────────────
  const [adminRunning, setAdminRunning] = useState(null);  // key string | null
  const [adminStatus,  setAdminStatus]  = useState(null);  // { ok, text } | null

  // ── Trigger to re-fetch patient data (incremented after admin actions) ────
  const [refreshTick, setRefreshTick] = useState(0);

  // ── Fetch patient list ────────────────────────────────────────────────────
  function loadPatients(autoSelectFirst = false) {
    setLoadingPatients(true);
    getPatients()
      .then((data) => {
        setPatients(data);
        if (autoSelectFirst && data.length > 0) {
          setSelectedId(data[0].id);
        }
      })
      .catch(console.error)
      .finally(() => setLoadingPatients(false));
  }

  // Initial load
  useEffect(() => {
    loadPatients(true);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ── Fetch all data for the selected patient ───────────────────────────────
  useEffect(() => {
    if (!selectedId) return;

    // Clear stale data and mark everything loading
    setSummary(null);
    setDailyMetrics([]);
    setAlerts([]);
    setEvents([]);
    setLoadingSummary(true);
    setLoadingMetrics(true);
    setLoadingAlerts(true);
    setLoadingEvents(true);

    getSummary(selectedId)
      .then(setSummary)
      .catch(console.error)
      .finally(() => setLoadingSummary(false));

    // Raw daily metric rows — available for debugging or future components
    getDailyMetrics(selectedId)
      .then(setDailyMetrics)
      .catch(console.error)
      .finally(() => setLoadingMetrics(false));

    // Open alerts only — AlertsPanel is designed for the open-alert list
    getAlerts(selectedId, "open")
      .then(setAlerts)
      .catch(console.error)
      .finally(() => setLoadingAlerts(false));

    getTimeline(selectedId, { limit: 100 })
      .then(setEvents)
      .catch(console.error)
      .finally(() => setLoadingEvents(false));

  }, [selectedId, refreshTick]);

  // ── Admin action handler ──────────────────────────────────────────────────
  async function handleAdminAction(key) {
    const action = ADMIN_ACTIONS.find((a) => a.key === key);
    if (!action || adminRunning) return;

    setAdminRunning(key);
    setAdminStatus(null);

    try {
      await action.fn();
      setAdminStatus({ ok: true, text: `${action.label} completed.` });

      // Seed may create new patients — reload the full patient list
      if (key === "seed") {
        loadPatients(/* autoSelectFirst = */ !selectedId);
      }

      // Refresh per-patient data so updated metrics/alerts appear immediately
      if (selectedId) {
        setRefreshTick((t) => t + 1);
      }
    } catch {
      setAdminStatus({ ok: false, text: `${action.label} failed.` });
    } finally {
      setAdminRunning(null);
      // Auto-clear the status message after 4 s
      setTimeout(() => setAdminStatus(null), 4000);
    }
  }

  // ── Render ────────────────────────────────────────────────────────────────
  return (
    <Layout
      patients={patients}
      selectedPatientId={selectedId}
      onSelectPatient={setSelectedId}
      loadingPatients={loadingPatients}
    >
      {/* Row 0 — Admin actions */}
      <AdminStrip
        running={adminRunning}
        status={adminStatus}
        onRun={handleAdminAction}
      />

      {/* No patients guard */}
      {!loadingPatients && patients.length === 0 ? (
        <div className="flex items-center justify-center h-64">
          <div className="text-center space-y-1">
            <p className="text-sm text-gray-500">No patients found.</p>
            <p className="text-xs text-gray-700">
              Click <span className="text-gray-500">Seed Demo Data</span> to populate the database.
            </p>
          </div>
        </div>
      ) : (
        <>
          {/* Row 1 — Six metric overview tiles */}
          <OverviewCards summary={summary} loading={loadingSummary} />

          {/* Data source provenance note — only renders when summary is loaded */}
          {!loadingSummary && (
            <DataSourceNote sources={summary?.data_sources ?? null} />
          )}

          {/* Row 2 — Trend charts (left 2/3) + Open alerts (right 1/3) */}
          <div className="grid grid-cols-3 gap-5 items-stretch">
            <div className="col-span-2">
              <TrendCharts summary={summary} loading={loadingSummary} />
            </div>
            <AlertsPanel alerts={alerts} loading={loadingAlerts} />
          </div>

          {/* Row 3 — Clinical summary (left) + Event timeline (right) */}
          <div className="grid grid-cols-2 gap-5">
            <ClinicalSummary summary={summary} loading={loadingSummary} />
            <EventTimeline   events={events}   loading={loadingEvents}  />
          </div>

          {/* Row 4 — Report preview */}
          <ReportPreview
            patient={patients.find((p) => p.id === selectedId) ?? null}
            summary={summary}
            alerts={alerts}
            loading={loadingSummary}
          />
        </>
      )}
    </Layout>
  );
}
