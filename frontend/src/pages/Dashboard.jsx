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
  importPipelineData,
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

// Ordered steps run by "Initialize Demo"
const INIT_STEPS = [
  { label: "Seeding patients…",     fn: seedDemoData                        },
  { label: "Importing pipeline…",   fn: () => importPipelineData(1)         },
  { label: "Computing metrics…",    fn: computeMetrics                      },
  { label: "Generating alerts…",    fn: generateAlerts                      },
];

// ── Shared status pill ────────────────────────────────────────────────────────

function StatusPill({ status }) {
  if (!status) return null;
  return (
    <span className={`text-xs flex items-center gap-1.5 ml-1 ${status.ok ? "text-green-400" : "text-red-400"}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${status.ok ? "bg-green-400" : "bg-red-400"}`} />
      {status.text}
    </span>
  );
}

// ── Admin strip ───────────────────────────────────────────────────────────────

function AdminStrip({ running, status, onRun, initRunning, initStep, initStatus, onInitialize }) {
  const busy = running !== null || initRunning;

  return (
    <div className="flex items-center gap-2 flex-wrap">

      {/* ── Initialize Demo — primary CTA ── */}
      <button
        onClick={onInitialize}
        disabled={busy}
        className="text-xs px-3 py-1.5 rounded border border-teal-800 text-teal-400
                   hover:border-teal-600 hover:text-teal-300
                   disabled:opacity-40 disabled:cursor-not-allowed
                   transition-colors flex items-center gap-1.5"
      >
        {initRunning ? (
          <>
            <span className="w-2.5 h-2.5 rounded-full border border-teal-400/30
                             border-t-teal-400 animate-spin flex-shrink-0" />
            {initStep ?? "Initializing…"}
          </>
        ) : "Initialize Demo"}
      </button>

      {/* Divider */}
      <span className="text-gray-800 select-none text-sm">|</span>

      {/* ── Individual admin buttons ── */}
      {ADMIN_ACTIONS.map(({ key, label }) => (
        <button
          key={key}
          onClick={() => onRun(key)}
          disabled={busy}
          className="text-xs px-3 py-1.5 rounded border border-gray-800 text-gray-500
                     hover:border-gray-600 hover:text-gray-300
                     disabled:opacity-40 disabled:cursor-not-allowed
                     transition-colors"
        >
          {running === key ? "Running…" : label}
        </button>
      ))}

      <StatusPill status={initStatus} />
      <StatusPill status={status} />
    </div>
  );
}

// ── Tab bar ───────────────────────────────────────────────────────────────────

const TABS = [
  { key: "dashboard",    label: "Dashboard"     },
  { key: "source-video", label: "Source Video"  },
];

function TabBar({ active, onChange }) {
  return (
    <div className="flex items-center gap-1 border-b border-gray-800 -mx-4 md:-mx-6 px-4 md:px-6 mb-1">
      {TABS.map(({ key, label }) => {
        const isActive = active === key;
        return (
          <button
            key={key}
            onClick={() => onChange(key)}
            className={`
              text-xs font-medium px-3 py-2.5 border-b-2 transition-colors whitespace-nowrap
              ${isActive
                ? "border-teal-400 text-teal-400"
                : "border-transparent text-gray-500 hover:text-gray-300 hover:border-gray-700"}
            `}
          >
            {label}
          </button>
        );
      })}
    </div>
  );
}

// ── Source video view ─────────────────────────────────────────────────────────

function SourceVideoView() {
  return (
    <div className="flex flex-col items-center gap-5 py-4">
      <div className="w-full max-w-3xl">
        <video
          src="/videodemo.mp4"
          controls
          className="w-full rounded-xl border border-gray-800 bg-gray-900 shadow-xl"
          style={{ maxHeight: "70vh" }}
        >
          Your browser does not support the video tag.
        </video>
        <p className="mt-4 text-xs text-gray-500 leading-relaxed text-center max-w-2xl mx-auto">
          This sample video is used as the upstream input to the MITRA pipeline.
          The resulting pipeline outputs are then mapped into the Alzheimer&apos;s monitoring dashboard.
        </p>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function Dashboard() {

  // ── Active tab ────────────────────────────────────────────────────────────
  const [activeTab, setActiveTab] = useState("dashboard");

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

  // ── Initialize Demo state ─────────────────────────────────────────────────
  const [initRunning, setInitRunning] = useState(false);
  const [initStep,    setInitStep]    = useState(null);   // current step label
  const [initStatus,  setInitStatus]  = useState(null);   // { ok, text } | null

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

  // ── Initialize Demo handler ───────────────────────────────────────────────
  async function handleInitializeDemo() {
    if (initRunning || adminRunning) return;

    setInitRunning(true);
    setInitStatus(null);

    try {
      for (const step of INIT_STEPS) {
        setInitStep(step.label);
        await step.fn();
      }
      setInitStatus({ ok: true, text: "Demo initialized." });
      // Reload patient list (seed may have added patients) and refresh data
      loadPatients(/* autoSelectFirst = */ !selectedId);
      setRefreshTick((t) => t + 1);
    } catch (err) {
      const detail = err?.response?.data?.detail ?? err?.message ?? "Unknown error";
      setInitStatus({ ok: false, text: `Initialization failed: ${detail}` });
    } finally {
      setInitStep(null);
      setInitRunning(false);
      setTimeout(() => setInitStatus(null), 6000);
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
      {/* Tab bar — sits flush against Layout's horizontal padding */}
      <TabBar active={activeTab} onChange={setActiveTab} />

      {/* ── Source Video tab ── */}
      {activeTab === "source-video" && <SourceVideoView />}

      {/* ── Dashboard tab ── */}
      {activeTab === "dashboard" && (
        <>
          {/* Row 0 — Admin actions */}
          <AdminStrip
            running={adminRunning}
            status={adminStatus}
            onRun={handleAdminAction}
            initRunning={initRunning}
            initStep={initStep}
            initStatus={initStatus}
            onInitialize={handleInitializeDemo}
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
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5 items-stretch">
                <div className="md:col-span-2">
                  <TrendCharts summary={summary} loading={loadingSummary} />
                </div>
                <AlertsPanel alerts={alerts} loading={loadingAlerts} />
              </div>

              {/* Row 3 — Clinical summary (left) + Event timeline (right) */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
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
        </>
      )}
    </Layout>
  );
}
