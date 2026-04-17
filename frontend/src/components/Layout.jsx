import { useState } from "react";
import PatientSelector from "./PatientSelector.jsx";

/**
 * Root shell: fixed top header + left sidebar + scrollable main area.
 *
 * Desktop (md+): fixed 224px sidebar on the left, main fills remaining width.
 * Mobile (<md):  sidebar hidden; a compact patient <select> is shown between
 *                the header and the main content area.
 */
export default function Layout({
  patients,
  selectedPatientId,
  onSelectPatient,
  loadingPatients,
  children,
}) {
  return (
    <div className="h-screen flex flex-col bg-gray-950 text-gray-100 font-sans overflow-hidden">

      {/* ── Top header ─────────────────────────────────────────────────── */}
      <header className="flex-shrink-0 h-14 border-b border-gray-800 px-4 md:px-6 flex items-center gap-2 md:gap-3">
        <div className="flex items-center gap-2 md:gap-2.5">
          <div className="w-6 h-6 rounded bg-teal-400/20 flex items-center justify-center flex-shrink-0">
            <div className="w-2.5 h-2.5 rounded-full bg-teal-400" />
          </div>
          <span className="font-semibold tracking-wide text-sm text-gray-100">MITRA</span>
        </div>
        <span className="text-gray-600 text-xs">·</span>
        {/* Hide subtitle on very small screens to prevent overflow */}
        <span className="text-gray-500 text-xs hidden sm:inline truncate">
          Alzheimer's &amp; Dementia Monitoring
        </span>

        <div className="ml-auto flex items-center gap-3 flex-shrink-0">
          <span className="text-xs text-gray-600 border border-gray-800 rounded px-2 md:px-2.5 py-1 whitespace-nowrap">
            <span className="hidden sm:inline">iHelp Robotics · </span>Demo
          </span>
        </div>
      </header>

      {/* ── Mobile patient picker — visible only below md breakpoint ───── */}
      <div className="md:hidden flex-shrink-0 border-b border-gray-800 px-4 py-2 bg-gray-950">
        {loadingPatients ? (
          <div className="h-8 bg-gray-800 rounded-lg animate-pulse" />
        ) : patients.length === 0 ? (
          <p className="text-xs text-gray-700 py-1">No patients — seed demo data first.</p>
        ) : (
          <select
            value={selectedPatientId ?? ""}
            onChange={(e) => onSelectPatient(Number(e.target.value))}
            className="w-full bg-gray-900 border border-gray-800 text-gray-200 text-sm
                       rounded-lg px-3 py-1.5 focus:outline-none focus:border-gray-600
                       appearance-none"
          >
            {patients.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}{p.age ? ` — Age ${p.age}` : ""}
              </option>
            ))}
          </select>
        )}
      </div>

      {/* ── Body ──────────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Sidebar — hidden on mobile, visible md+ */}
        <aside className="hidden md:flex w-56 flex-shrink-0 border-r border-gray-800 flex-col overflow-hidden bg-gray-950">
          <PatientSelector
            patients={patients}
            selectedId={selectedPatientId}
            onSelect={onSelectPatient}
            loading={loadingPatients}
          />

          {/* Sidebar footer */}
          <div className="flex-shrink-0 px-5 py-4 border-t border-gray-800">
            <p className="text-xs text-gray-700">Phase 1 — 6 metrics</p>
            <p className="text-xs text-gray-700 mt-0.5">v 0.1.0</p>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4 md:space-y-5 min-w-0">
          {children}
        </main>
      </div>
    </div>
  );
}
