import PatientSelector from "./PatientSelector.jsx";

/**
 * Root shell: fixed top header + left sidebar + scrollable main area.
 * Matches the dark aesthetic already in the project (gray-950 / teal accents).
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
      <header className="flex-shrink-0 h-14 border-b border-gray-800 px-6 flex items-center gap-3">
        <div className="flex items-center gap-2.5">
          <div className="w-6 h-6 rounded bg-teal-400/20 flex items-center justify-center">
            <div className="w-2.5 h-2.5 rounded-full bg-teal-400" />
          </div>
          <span className="font-semibold tracking-wide text-sm text-gray-100">MITRA</span>
        </div>
        <span className="text-gray-600 text-xs">·</span>
        <span className="text-gray-500 text-xs">Alzheimer's &amp; Dementia Monitoring</span>

        <div className="ml-auto flex items-center gap-3">
          <span className="text-xs text-gray-600 border border-gray-800 rounded px-2.5 py-1">
            iHelp Robotics · Demo
          </span>
        </div>
      </header>

      {/* ── Body ──────────────────────────────────────────────────────── */}
      <div className="flex flex-1 overflow-hidden">

        {/* Sidebar */}
        <aside className="w-56 flex-shrink-0 border-r border-gray-800 flex flex-col overflow-hidden bg-gray-950">
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
        <main className="flex-1 overflow-y-auto p-6 space-y-5">
          {children}
        </main>
      </div>
    </div>
  );
}
