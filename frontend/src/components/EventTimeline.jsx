/**
 * EventTimeline — chronological clinical event list.
 *
 * Props:
 *   events   EventRead[]   from GET /patients/:id/timeline (ascending order from API)
 *   loading  boolean
 *
 * Displays newest events at the top. Each row shows the event type badge,
 * subtype (from metadata_json), severity, and human-readable timestamp.
 */

// ── Event type config ────────────────────────────────────────────────────────

// Keys match EventType string values returned by the API (lowercase snake_case).
const EVENT_CFG = {
  wandering_episode: {
    label: "Wandering",
    dot:   "bg-amber-400",
    badge: "text-amber-400 bg-amber-400/10",
  },
  wrong_turn: {
    label: "Wrong Turn",
    dot:   "bg-yellow-400",
    badge: "text-yellow-400 bg-yellow-400/10",
  },
  fall: {
    label: "Fall",
    dot:   "bg-red-400",
    badge: "text-red-400 bg-red-400/10",
  },
  agitation: {
    label: "Agitation",
    dot:   "bg-purple-400",
    badge: "text-purple-400 bg-purple-400/10",
  },
};

const SEVERITY_TEXT = {
  info:     "text-blue-400",
  warning:  "text-amber-400",
  critical: "text-red-400",
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function fmtTimestamp(ts) {
  const d = new Date(ts);
  return d.toLocaleString("en-GB", {
    day:    "numeric",
    month:  "short",
    hour:   "2-digit",
    minute: "2-digit",
  });
}

function humanSubtype(s) {
  // "wandering_episode_started" → "episode started"
  if (!s) return null;
  return s.replace(/_/g, " ").replace(/^[a-z]/, (c) => c.toUpperCase());
}

// ── Single row ────────────────────────────────────────────────────────────────

function EventRow({ event }) {
  const cfg      = EVENT_CFG[event.event_type] ?? { label: event.event_type, dot: "bg-gray-500", badge: "text-gray-400 bg-gray-800" };
  const subtype  = humanSubtype(event.metadata_json?.subtype);
  const sevColor = SEVERITY_TEXT[event.severity] ?? "text-gray-500";

  return (
    <div className="flex items-start gap-3 py-3 border-b border-gray-800 last:border-0">
      {/* Colour dot */}
      <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${cfg.dot}`} />

      <div className="flex-1 min-w-0">
        {/* Top row: type badge + subtype + severity */}
        <div className="flex items-center flex-wrap gap-1.5">
          <span className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium ${cfg.badge}`}>
            {cfg.label}
          </span>
          {subtype && (
            <span className="text-xs text-gray-500">{subtype}</span>
          )}
          <span className={`ml-auto text-xs flex-shrink-0 ${sevColor}`}>
            {event.severity}
          </span>
        </div>

        {/* Timestamp */}
        <p className="text-xs text-gray-600 mt-1">{fmtTimestamp(event.timestamp)}</p>

        {/* Location pill (if GPS available) */}
        {event.lat !== null && event.lng !== null && (
          <p className="text-xs text-gray-700 mt-0.5">
            {event.lat.toFixed(4)}, {event.lng.toFixed(4)}
          </p>
        )}
      </div>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="space-y-1">
      {Array(6).fill(null).map((_, i) => (
        <div key={i} className="flex items-start gap-3 py-3 border-b border-gray-800">
          <div className="w-1.5 h-1.5 rounded-full mt-1.5 bg-gray-700 flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="flex gap-2">
              <div className="h-4 bg-gray-800 rounded-full animate-pulse w-20" />
              <div className="h-4 bg-gray-800 rounded animate-pulse w-28" />
            </div>
            <div className="h-3 bg-gray-800 rounded animate-pulse w-24" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function EventTimeline({ events, loading }) {
  // Show newest first
  const sorted = loading ? [] : [...events].reverse();

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      {/* Header */}
      <div className="flex items-center justify-between mb-4">
        <p className="text-xs text-gray-500">Event Timeline</p>
        {!loading && (
          <p className="text-xs text-gray-700">{events.length} events</p>
        )}
      </div>

      {/* Body */}
      {loading ? (
        <Skeleton />
      ) : events.length === 0 ? (
        <p className="text-xs text-gray-600 py-6 text-center">
          No events recorded for this patient.
        </p>
      ) : (
        <div className="max-h-72 overflow-y-auto pr-1">
          {sorted.map((e) => (
            <EventRow key={e.id} event={e} />
          ))}
        </div>
      )}
    </div>
  );
}
