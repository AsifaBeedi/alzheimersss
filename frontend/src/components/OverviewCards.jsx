/**
 * OverviewCards — six Phase 1 metric tiles.
 *
 * Props:
 *   summary   object|null   from GET /patients/:id/summary (latest_* fields used)
 *   loading   boolean
 *
 * Each card derives a status (good / warn / critical / none) from its value
 * using simple clinical thresholds and colours the status dot accordingly.
 */

// ── Threshold helpers ──────────────────────────────────────────────────────

/** Returns "good" | "warn" | "critical" | "none" for a "higher is better" metric. */
function hiStatus(value, good, warn) {
  if (value === null || value === undefined) return "none";
  if (value >= good) return "good";
  if (value >= warn) return "warn";
  return "critical";
}

/** Returns status for a "lower is better" metric (e.g. fall count, wandering). */
function loStatus(value, good, warn) {
  if (value === null || value === undefined) return "none";
  if (value <= good) return "good";
  if (value <= warn) return "warn";
  return "critical";
}

const STATUS = {
  good:     { dot: "bg-green-400",  text: "text-green-400",  label: "Normal"   },
  warn:     { dot: "bg-amber-400",  text: "text-amber-400",  label: "Monitor"  },
  critical: { dot: "bg-red-400",    text: "text-red-400",    label: "Review"   },
  none:     { dot: "bg-gray-700",   text: "text-gray-600",   label: "No data"  },
};

// ── Single card ─────────────────────────────────────────────────────────────

function MetricCard({ label, displayValue, unit, status }) {
  const s = STATUS[status] ?? STATUS.none;
  const hasValue = displayValue !== null && displayValue !== undefined;

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-3">
      {/* Header row: label + status dot */}
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 leading-none">{label}</span>
        <div className={`w-2 h-2 rounded-full flex-shrink-0 ${s.dot}`} title={s.label} />
      </div>

      {/* Value */}
      <div>
        <p className={`text-2xl font-bold leading-none ${hasValue ? "text-gray-100" : "text-gray-700"}`}>
          {hasValue ? displayValue : "—"}
          {hasValue && unit && (
            <span className="text-sm font-normal text-gray-500 ml-1">{unit}</span>
          )}
        </p>
        <p className={`text-xs mt-1.5 ${s.text}`}>{s.label}</p>
      </div>
    </div>
  );
}

// ── Skeleton ─────────────────────────────────────────────────────────────────

function CardSkeleton() {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-3">
      <div className="flex items-center justify-between">
        <div className="h-2.5 bg-gray-800 rounded animate-pulse w-2/3" />
        <div className="w-2 h-2 rounded-full bg-gray-800 animate-pulse" />
      </div>
      <div>
        <div className="h-7 bg-gray-800 rounded animate-pulse w-1/2 mb-2" />
        <div className="h-2.5 bg-gray-800 rounded animate-pulse w-1/3" />
      </div>
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

export default function OverviewCards({ summary, loading }) {
  if (loading) {
    return (
      <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4">
        {Array(6).fill(null).map((_, i) => <CardSkeleton key={i} />)}
      </div>
    );
  }

  const score    = summary?.latest_independence_score    ?? null;
  const wander   = summary?.latest_wandering_count       ?? null;
  const falls    = summary?.latest_fall_count            ?? null;
  const radius   = summary?.latest_movement_radius_m     ?? null;
  const wear     = summary?.latest_wear_hours            ?? null;
  const wrong    = summary?.latest_wrong_turn_count      ?? null;

  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 xl:grid-cols-6 gap-4">
      <MetricCard
        label="Independence Score"
        displayValue={score !== null ? score.toFixed(1) : null}
        unit="/ 100"
        status={hiStatus(score, 70, 40)}
      />
      <MetricCard
        label="Wandering Episodes"
        displayValue={wander}
        unit={wander === 1 ? "today" : "today"}
        status={loStatus(wander, 0, 2)}
      />
      <MetricCard
        label="Fall Events"
        displayValue={falls}
        unit={falls === 1 ? "fall" : "falls"}
        status={loStatus(falls, 0, 1)}
      />
      <MetricCard
        label="Movement Radius"
        displayValue={radius !== null ? Math.round(radius) : null}
        unit="m"
        status={radius === null ? "none" : "good"}
      />
      <MetricCard
        label="Wear Adherence"
        displayValue={wear !== null ? wear.toFixed(1) : null}
        unit="h"
        status={hiStatus(wear, 6, 3)}
      />
      <MetricCard
        label="Wrong Turns"
        displayValue={wrong}
        unit={wrong === 1 ? "turn" : "turns"}
        status={loStatus(wrong, 0, 2)}
      />
    </div>
  );
}
