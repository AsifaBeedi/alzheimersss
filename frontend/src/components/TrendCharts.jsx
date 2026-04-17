/**
 * TrendCharts — four 30-day Recharts panels in a 2×2 grid.
 *
 * Props:
 *   summary   object|null   from GET /patients/:id/summary (trend_* arrays used)
 *   loading   boolean
 *
 * Each trend_* array contains TrendPoint objects: { metric_date: "YYYY-MM-DD", value: number|null }
 * Recharts handles empty data gracefully (renders blank axes).
 */

import {
  LineChart,
  Line,
  BarChart,
  Bar,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
} from "recharts";

// ── Shared axis / grid styles ────────────────────────────────────────────────

const AXIS_TICK   = { fill: "#6b7280", fontSize: 10 };
const GRID_PROPS  = { stroke: "#1f2937", strokeDasharray: "3 3" };
const MARGIN      = { top: 4, right: 6, bottom: 0, left: -20 };

// ── Date formatter for XAxis ticks ──────────────────────────────────────────

const fmtDate = (d) => {
  if (!d) return "";
  // Parse as UTC midnight to avoid timezone drift on label
  const dt = new Date(d + "T00:00:00");
  return dt.toLocaleDateString("en-GB", { month: "short", day: "numeric" });
};

// ── Dark tooltip ─────────────────────────────────────────────────────────────

function DarkTooltip({ active, payload, label, unit = "" }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-gray-800 border border-gray-700 rounded-lg px-3 py-2 text-xs shadow-xl">
      <p className="text-gray-400 mb-1">{fmtDate(label)}</p>
      {payload.map((p, i) => (
        <p key={i} style={{ color: p.stroke || p.fill || p.color }}>
          {p.name}:{" "}
          {p.value !== null && p.value !== undefined
            ? `${Number(p.value).toFixed(1)}${unit}`
            : "—"}
        </p>
      ))}
    </div>
  );
}

// ── Chart card wrapper ────────────────────────────────────────────────────────

function ChartCard({ title, children, loading }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5">
      <p className="text-xs text-gray-500 mb-4">{title}</p>
      {loading ? (
        <div className="h-40 bg-gray-800 rounded-lg animate-pulse" />
      ) : (
        <div style={{ height: 160 }}>{children}</div>
      )}
    </div>
  );
}

// ── Main component ──────────────────────────────────────────────────────────

export default function TrendCharts({ summary, loading }) {
  const scoreData    = summary?.trend_independence_score ?? [];
  const radiusData   = summary?.trend_movement_radius_m  ?? [];
  const wanderData   = summary?.trend_wandering_count    ?? [];
  const wrongData    = summary?.trend_wrong_turn_count   ?? [];

  return (
    <div className="grid grid-cols-2 gap-4">

      {/* ── Independence Score ──────────────────────────────────────── */}
      <ChartCard title="Independence Score — 30 days" loading={loading}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={scoreData} margin={MARGIN}>
            <CartesianGrid {...GRID_PROPS} />
            <XAxis
              dataKey="metric_date"
              tickFormatter={fmtDate}
              tick={AXIS_TICK}
              interval="preserveStartEnd"
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              domain={[0, 100]}
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
            />
            <ReferenceLine y={70} stroke="#d97706" strokeDasharray="4 3" strokeWidth={1} />
            <ReferenceLine y={40} stroke="#ef4444" strokeDasharray="4 3" strokeWidth={1} />
            <Tooltip content={<DarkTooltip unit="" />} />
            <Line
              dataKey="value"
              name="Score"
              stroke="#2dd4bf"
              strokeWidth={1.5}
              dot={false}
              connectNulls
              activeDot={{ r: 3, fill: "#2dd4bf" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ── Movement Radius ─────────────────────────────────────────── */}
      <ChartCard title="Movement Radius — 30 days" loading={loading}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={radiusData} margin={MARGIN}>
            <CartesianGrid {...GRID_PROPS} />
            <XAxis
              dataKey="metric_date"
              tickFormatter={fmtDate}
              tick={AXIS_TICK}
              interval="preserveStartEnd"
              tickLine={false}
              axisLine={false}
            />
            <YAxis tick={AXIS_TICK} tickLine={false} axisLine={false} />
            <Tooltip content={<DarkTooltip unit="m" />} />
            <Line
              dataKey="value"
              name="Radius"
              stroke="#a78bfa"
              strokeWidth={1.5}
              dot={false}
              connectNulls
              activeDot={{ r: 3, fill: "#a78bfa" }}
            />
          </LineChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ── Wandering Episodes ──────────────────────────────────────── */}
      <ChartCard title="Wandering Episodes — 30 days" loading={loading}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={wanderData} margin={MARGIN}>
            <CartesianGrid {...GRID_PROPS} />
            <XAxis
              dataKey="metric_date"
              tickFormatter={fmtDate}
              tick={AXIS_TICK}
              interval="preserveStartEnd"
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              allowDecimals={false}
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<DarkTooltip unit=" ep" />} />
            <Bar
              dataKey="value"
              name="Episodes"
              fill="#f59e0b"
              radius={[2, 2, 0, 0]}
              maxBarSize={18}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

      {/* ── Wrong Turns ─────────────────────────────────────────────── */}
      <ChartCard title="Wrong Turns — 30 days" loading={loading}>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={wrongData} margin={MARGIN}>
            <CartesianGrid {...GRID_PROPS} />
            <XAxis
              dataKey="metric_date"
              tickFormatter={fmtDate}
              tick={AXIS_TICK}
              interval="preserveStartEnd"
              tickLine={false}
              axisLine={false}
            />
            <YAxis
              allowDecimals={false}
              tick={AXIS_TICK}
              tickLine={false}
              axisLine={false}
            />
            <Tooltip content={<DarkTooltip unit=" turns" />} />
            <Bar
              dataKey="value"
              name="Wrong Turns"
              fill="#f87171"
              radius={[2, 2, 0, 0]}
              maxBarSize={18}
            />
          </BarChart>
        </ResponsiveContainer>
      </ChartCard>

    </div>
  );
}
