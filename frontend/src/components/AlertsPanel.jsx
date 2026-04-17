/**
 * AlertsPanel — open alert list.
 *
 * Props:
 *   alerts   AlertRead[]   from summary.open_alerts or GET /patients/:id/alerts
 *   loading  boolean
 *
 * AlertRead shape:
 *   { id, patient_id, alert_type, severity, description, timestamp, status, metadata_json }
 */

// ── Config maps ──────────────────────────────────────────────────────────────

// Keys match AlertType string values returned by the API (lowercase snake_case).
const ALERT_TYPE_LABEL = {
  wandering:        "Wandering",
  fall:             "Fall",
  low_adherence:    "Low Adherence",
  low_independence: "Low Independence",
};

const SEVERITY = {
  critical: {
    dot:   "bg-red-400",
    badge: "text-red-400 bg-red-400/10",
    ring:  "border-red-900",
  },
  warning: {
    dot:   "bg-amber-400",
    badge: "text-amber-400 bg-amber-400/10",
    ring:  "border-amber-900",
  },
  info: {
    dot:   "bg-blue-400",
    badge: "text-blue-400 bg-blue-400/10",
    ring:  "border-blue-900",
  },
};

const STATUS_LABEL = {
  open:         { text: "Open",         color: "text-gray-500" },
  acknowledged: { text: "Acknowledged", color: "text-teal-500" },
  resolved:     { text: "Resolved",     color: "text-green-500" },
};

// ── Helpers ──────────────────────────────────────────────────────────────────

function relativeTime(ts) {
  const diffMs  = Date.now() - new Date(ts).getTime();
  const diffMin = Math.round(diffMs / 60_000);
  if (diffMin <  1)  return "Just now";
  if (diffMin <  60) return `${diffMin}m ago`;
  const diffH = Math.round(diffMin / 60);
  if (diffH   <  24) return `${diffH}h ago`;
  const diffD = Math.round(diffH / 24);
  if (diffD   <   7) return `${diffD}d ago`;
  return new Date(ts).toLocaleDateString("en-GB", { day: "numeric", month: "short" });
}

// ── Single alert row ─────────────────────────────────────────────────────────

function AlertRow({ alert }) {
  const sev       = SEVERITY[alert.severity]    ?? SEVERITY.info;
  const typeLabel = ALERT_TYPE_LABEL[alert.alert_type] ?? alert.alert_type;
  const statusCfg = STATUS_LABEL[alert.status]  ?? STATUS_LABEL.open;

  return (
    <div className={`flex items-start gap-3 py-3.5 border-b border-gray-800 last:border-0`}>
      {/* Severity dot */}
      <div className={`w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0 ${sev.dot}`} />

      <div className="flex-1 min-w-0">
        {/* Top row: type badge + status + time */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${sev.badge}`}>
            {typeLabel}
          </span>
          <span className={`text-xs ${statusCfg.color}`}>
            {statusCfg.text}
          </span>
          <span className="text-xs text-gray-600 ml-auto flex-shrink-0">
            {relativeTime(alert.timestamp)}
          </span>
        </div>

        {/* Description */}
        <p className="text-xs text-gray-400 mt-1.5 leading-relaxed line-clamp-2">
          {alert.description}
        </p>
      </div>
    </div>
  );
}

// ── Summary counts ───────────────────────────────────────────────────────────

function CountBadge({ count, label, color }) {
  if (!count) return null;
  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${color}`}>
      {count} {label}
    </span>
  );
}

// ── Skeleton ─────────────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="space-y-0.5">
      {Array(4).fill(null).map((_, i) => (
        <div key={i} className="flex items-start gap-3 py-3.5 border-b border-gray-800">
          <div className="w-1.5 h-1.5 rounded-full mt-1.5 bg-gray-800 flex-shrink-0" />
          <div className="flex-1 space-y-2">
            <div className="flex items-center gap-2">
              <div className="h-4 bg-gray-800 rounded-full animate-pulse w-24" />
              <div className="h-3 bg-gray-800 rounded animate-pulse w-16" />
              <div className="h-3 bg-gray-800 rounded animate-pulse w-10 ml-auto" />
            </div>
            <div className="h-3 bg-gray-800 rounded animate-pulse w-full" />
            <div className="h-3 bg-gray-800 rounded animate-pulse w-3/4" />
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyState() {
  return (
    <div className="flex flex-col items-center justify-center py-10 gap-3">
      <div className="w-10 h-10 rounded-full bg-green-400/10 flex items-center justify-center">
        <div className="w-4 h-4 rounded-full bg-green-400/40 flex items-center justify-center">
          <div className="w-2 h-2 rounded-full bg-green-400" />
        </div>
      </div>
      <div className="text-center">
        <p className="text-xs text-gray-500">No open alerts</p>
        <p className="text-xs text-gray-700 mt-0.5">All thresholds within range</p>
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function AlertsPanel({ alerts, loading }) {
  const critical = alerts.filter((a) => a.severity === "critical").length;
  const warning  = alerts.filter((a) => a.severity === "warning").length;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between mb-1 flex-shrink-0">
        <p className="text-xs text-gray-500">Open Alerts</p>

        {!loading && alerts.length > 0 && (
          <div className="flex items-center gap-1.5">
            <CountBadge
              count={critical}
              label={critical === 1 ? "critical" : "critical"}
              color="text-red-400 bg-red-400/10"
            />
            <CountBadge
              count={warning}
              label={warning === 1 ? "warning" : "warning"}
              color="text-amber-400 bg-amber-400/10"
            />
          </div>
        )}
      </div>

      {/* Total count subtitle */}
      {!loading && alerts.length > 0 && (
        <p className="text-xs text-gray-700 mb-3">
          {alerts.length} unresolved
        </p>
      )}

      {/* Body */}
      <div className="flex-1 overflow-y-auto min-h-0">
        {loading ? (
          <Skeleton />
        ) : alerts.length === 0 ? (
          <EmptyState />
        ) : (
          alerts.map((a) => <AlertRow key={a.id} alert={a} />)
        )}
      </div>
    </div>
  );
}
