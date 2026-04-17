/**
 * PatientSelector — sidebar patient list.
 *
 * Props:
 *   patients   Patient[]   list from GET /patients
 *   selectedId number|null currently active patient id
 *   onSelect   (id) => void
 *   loading    boolean
 */

function Skeleton() {
  return (
    <div className="space-y-1 px-3">
      {[1, 2].map((i) => (
        <div key={i} className="flex items-center gap-3 px-3 py-2.5 rounded-lg">
          <div className="w-8 h-8 rounded-full bg-gray-800 animate-pulse flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="h-2.5 bg-gray-800 rounded animate-pulse w-3/4" />
            <div className="h-2 bg-gray-800 rounded animate-pulse w-1/2" />
          </div>
        </div>
      ))}
    </div>
  );
}

function PatientRow({ patient, selected, onSelect }) {
  // Two-letter initials from first and last word of name
  const parts = patient.name.split(" ").filter(Boolean);
  const initials = (
    (parts[0]?.[0] ?? "") + (parts[parts.length - 1]?.[0] ?? "")
  ).toUpperCase();

  return (
    <button
      onClick={() => onSelect(patient.id)}
      className={`w-full text-left flex items-center gap-3 px-3 py-2.5 rounded-lg transition-colors group ${
        selected
          ? "bg-teal-400/10 text-teal-300"
          : "text-gray-400 hover:bg-gray-800 hover:text-gray-200"
      }`}
    >
      {/* Avatar */}
      <div
        className={`w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold flex-shrink-0 ${
          selected
            ? "bg-teal-400/20 text-teal-300"
            : "bg-gray-800 text-gray-500 group-hover:text-gray-300"
        }`}
      >
        {initials}
      </div>

      {/* Info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate leading-tight">{patient.name}</p>
        <p className="text-xs text-gray-600 mt-0.5">
          {patient.age ? `Age ${patient.age}` : ""}
          {patient.gender ? ` · ${patient.gender}` : ""}
        </p>
      </div>

      {/* Active indicator */}
      {selected && (
        <div className="w-1.5 h-1.5 rounded-full bg-teal-400 flex-shrink-0" />
      )}
    </button>
  );
}

export default function PatientSelector({ patients, selectedId, onSelect, loading }) {
  return (
    <div className="flex-1 overflow-y-auto py-4">
      <p className="text-xs font-medium text-gray-600 uppercase tracking-widest px-6 mb-3">
        Patients
      </p>

      {loading ? (
        <Skeleton />
      ) : patients.length === 0 ? (
        <p className="text-xs text-gray-700 px-6 py-2">No patients found.</p>
      ) : (
        <div className="space-y-0.5 px-3">
          {patients.map((p) => (
            <PatientRow
              key={p.id}
              patient={p}
              selected={p.id === selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}
