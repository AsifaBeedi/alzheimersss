/**
 * ReportPreview — Family Update and Clinical Summary preview cards.
 *
 * Props:
 *   patient  object|null   selected patient from GET /patients
 *   summary  object|null   from GET /patients/:id/summary
 *   alerts   Alert[]       from GET /patients/:id/alerts (open)
 *   loading  boolean
 *
 * Two side-by-side cards derived entirely from live API data.
 * No PDF export — display only.
 */

// ── Helpers ───────────────────────────────────────────────────────────────────

/** Mean of the last 7 non-null values vs the 7 before that. */
function trendDir(points) {
  if (!points?.length) return null;
  const vals = points
    .filter((p) => p.value !== null && p.value !== undefined)
    .map((p) => p.value);
  if (vals.length < 4) return null;
  const recent = vals.slice(-7);
  const prior  = vals.slice(-14, -7);
  if (!prior.length) return null;
  const mean  = (arr) => arr.reduce((a, b) => a + b, 0) / arr.length;
  const delta = mean(recent) - mean(prior);
  if (Math.abs(delta) < 0.5) return "stable";
  return delta > 0 ? "up" : "down";
}

function todayStr() {
  return new Date().toLocaleDateString("en-GB", {
    day: "numeric", month: "long", year: "numeric",
  });
}

/** Returns formatted string or em-dash if value is null/undefined. */
function fmt(value, fn) {
  if (value === null || value === undefined) return "—";
  return fn(value);
}

// ── Trend arrow ───────────────────────────────────────────────────────────────

function TrendArrow({ dir, positiveIsGood = true }) {
  if (!dir || dir === "stable") return <span className="text-gray-600 text-xs">→</span>;
  const isGood = positiveIsGood ? dir === "up" : dir === "down";
  return (
    <span className={`text-xs font-medium ${isGood ? "text-green-400" : "text-red-400"}`}>
      {dir === "up" ? "↑" : "↓"}
    </span>
  );
}

// ── Shared section header ─────────────────────────────────────────────────────

function SectionLabel({ text }) {
  return (
    <p className="text-xs text-gray-600 uppercase tracking-widest font-medium">{text}</p>
  );
}

// ── Family card ───────────────────────────────────────────────────────────────

function BulletRow({ text, variant = "default" }) {
  const styles = {
    default: { dot: "bg-gray-700",  text: "text-gray-400"  },
    good:    { dot: "bg-green-400", text: "text-gray-300"  },
    warn:    { dot: "bg-amber-400", text: "text-gray-300"  },
    alert:   { dot: "bg-red-400",   text: "text-red-300"   },
  };
  const s = styles[variant] ?? styles.default;
  return (
    <div className="flex items-start gap-2.5">
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-[5px] ${s.dot}`} />
      <p className={`text-sm leading-relaxed ${s.text}`}>{text}</p>
    </div>
  );
}

function FamilyCard({ patient, summary, alerts }) {
  const name  = patient?.name ?? "Patient";
  const first = name.split(" ")[0];

  const score  = summary?.latest_independence_score ?? null;
  const wander = summary?.latest_wandering_count    ?? null;
  const falls  = summary?.latest_fall_count         ?? null;
  const wear   = summary?.latest_wear_hours         ?? null;

  const scoreTrend   = trendDir(summary?.trend_independence_score);
  const criticalCount = alerts.filter((a) => a.severity === "critical").length;

  // ── Headline ──
  let headline, hlColor, hlSub;
  if (score === null) {
    headline = "Monitoring Active";
    hlColor  = "text-gray-400";
    hlSub    = "Awaiting metric data";
  } else if (criticalCount > 0) {
    headline = "Needs Attention";
    hlColor  = "text-red-400";
    hlSub    = `${criticalCount} critical alert${criticalCount > 1 ? "s" : ""} require review`;
  } else if (score >= 70 && scoreTrend !== "down") {
    headline = "Doing Well";
    hlColor  = "text-green-400";
    hlSub    = "All key indicators within normal range";
  } else if (score >= 50) {
    headline = "Stable";
    hlColor  = "text-amber-400";
    hlSub    = "Some metrics warrant monitoring";
  } else {
    headline = "Showing Concerns";
    hlColor  = "text-red-400";
    hlSub    = "Care team review recommended";
  }

  // ── Bullet content ──
  const bullets = [];

  // Independence score
  if (score === null) {
    bullets.push({ text: "Independence score is not yet available for this period.", variant: "default" });
  } else if (score >= 70) {
    bullets.push({ text: `${first}'s independence score is ${score.toFixed(0)}/100 — within the healthy range.`, variant: "good" });
  } else if (score >= 50) {
    bullets.push({ text: `${first}'s independence score is ${score.toFixed(0)}/100 — moderately reduced but manageable.`, variant: "warn" });
  } else {
    bullets.push({ text: `${first}'s independence score is ${score.toFixed(0)}/100 — below the expected range.`, variant: "alert" });
  }

  // Trend
  if (scoreTrend === "up")
    bullets.push({ text: `The score has been improving over the past week — a positive sign.`, variant: "good" });
  else if (scoreTrend === "down")
    bullets.push({ text: `The score has been declining recently. It may be worth checking in with the care team.`, variant: "warn" });

  // Safety
  const hasFalls   = falls !== null && falls > 0;
  const hasWander  = wander !== null && wander > 0;
  if (!hasFalls && !hasWander && falls !== null) {
    bullets.push({ text: "No falls or wandering episodes recorded recently.", variant: "good" });
  } else {
    const parts = [];
    if (hasFalls)  parts.push(`${falls} fall${falls > 1 ? "s" : ""}`);
    if (hasWander) parts.push(`${wander} wandering episode${wander > 1 ? "s" : ""}`);
    if (parts.length > 0)
      bullets.push({ text: `${parts.join(" and ")} recorded recently. Caregiver awareness recommended.`, variant: "warn" });
  }

  // Device wear
  if (wear !== null) {
    if (wear >= 6)
      bullets.push({ text: `Device worn for ${wear.toFixed(1)} hours today — monitoring is comprehensive.`, variant: "good" });
    else if (wear >= 3)
      bullets.push({ text: `Device worn for ${wear.toFixed(1)} hours — some periods may be unmonitored.`, variant: "warn" });
    else
      bullets.push({ text: `Device worn for only ${wear.toFixed(1)} hours. Encouraging consistent wear helps the care team.`, variant: "warn" });
  }

  // Alerts
  if (criticalCount > 0)
    bullets.push({ text: `${criticalCount} critical alert${criticalCount > 1 ? "s have" : " has"} been flagged — please discuss with the care team.`, variant: "alert" });
  else if (alerts.length > 1)
    bullets.push({ text: `${alerts.length} monitoring alerts are currently active and being tracked.`, variant: "default" });

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="text-xs font-semibold text-teal-400 uppercase tracking-widest">
            Family Update
          </span>
          <p className="text-base font-semibold text-gray-100 mt-1">{name}</p>
          <p className="text-xs text-gray-600 mt-0.5">{todayStr()}</p>
        </div>
        <div className="w-9 h-9 rounded-full bg-teal-400/10 flex items-center justify-center flex-shrink-0 mt-0.5">
          <div className="w-4 h-4 rounded-full bg-teal-400/30 flex items-center justify-center">
            <div className="w-2 h-2 rounded-full bg-teal-400" />
          </div>
        </div>
      </div>

      {/* Status headline */}
      <div className="border-t border-gray-800 pt-4">
        <p className={`text-2xl font-bold leading-tight tracking-tight ${hlColor}`}>
          {headline}
        </p>
        <p className="text-xs text-gray-600 mt-1">{hlSub}</p>
      </div>

      {/* Bullets */}
      <div className="space-y-3">
        {bullets.map((b, i) => (
          <BulletRow key={i} text={b.text} variant={b.variant} />
        ))}
      </div>

      {/* Footer */}
      <div className="border-t border-gray-800 pt-4 mt-auto">
        <p className="text-xs text-gray-700 leading-relaxed">
          Generated automatically from wearable sensor data.
          Contact the care team for a full clinical review.
        </p>
      </div>
    </div>
  );
}

// ── Clinical card ─────────────────────────────────────────────────────────────

function MetricRow({ label, value, unit, trendPoints, positiveIsGood = true }) {
  const dir = trendDir(trendPoints);
  return (
    <div className="flex items-center justify-between py-2 border-b border-gray-800 last:border-0">
      <span className="text-xs text-gray-500">{label}</span>
      <div className="flex items-center gap-2">
        <span className="text-xs font-mono font-medium text-gray-200">
          {value}
          {value !== "—" && unit ? (
            <span className="text-gray-600 font-normal ml-0.5">{unit}</span>
          ) : null}
        </span>
        <TrendArrow dir={dir} positiveIsGood={positiveIsGood} />
      </div>
    </div>
  );
}

function ClinicalCard({ patient, summary, alerts }) {
  const name      = patient?.name ?? "—";
  const patientId = patient?.id   ?? "—";

  const score  = summary?.latest_independence_score ?? null;
  const wander = summary?.latest_wandering_count    ?? null;
  const wrong  = summary?.latest_wrong_turn_count   ?? null;
  const radius = summary?.latest_movement_radius_m  ?? null;
  const wear   = summary?.latest_wear_hours         ?? null;
  const falls  = summary?.latest_fall_count         ?? null;

  const scoreTrend  = trendDir(summary?.trend_independence_score);
  const critical    = alerts.filter((a) => a.severity === "critical").length;
  const warning     = alerts.filter((a) => a.severity === "warning").length;

  // ── Assessment paragraph ──
  const sentences = [];

  // Score + trend
  if (score !== null) {
    const trendPhrase =
      scoreTrend === "up"     ? ", with an improving trend over the review period" :
      scoreTrend === "down"   ? ", with a declining trend over the review period"  :
                                "";
    sentences.push(
      `Patient presents with an independence score of ${score.toFixed(1)}/100${trendPhrase}.`
    );
  }

  // Safety events
  const safetyParts = [];
  if (falls !== null)  safetyParts.push(`${falls} fall event${falls !== 1 ? "s" : ""}`);
  if (wander !== null) safetyParts.push(`${wander} wandering episode${wander !== 1 ? "s" : ""}`);
  if (wrong  !== null) safetyParts.push(`${wrong} wrong turn${wrong !== 1 ? "s" : ""}`);
  if (safetyParts.length > 0) {
    const allClear = (falls === 0 && wander === 0 && wrong === 0);
    sentences.push(
      allClear
        ? "No safety events (falls, wandering, or navigation errors) recorded in the current period."
        : `Safety events recorded: ${safetyParts.join(", ")}.`
    );
  }

  // Radius
  if (radius !== null) {
    const m = Math.round(radius);
    const mobility =
      m > 500 ? "community-level mobility" :
      m > 200 ? "neighbourhood-level mobility" :
      m > 50  ? "activity largely confined to the home area" :
                "near-homebound movement pattern";
    sentences.push(`Movement radius of ${m} m indicates ${mobility}.`);
  }

  // Wear
  if (wear !== null) {
    const adequate = wear >= 6 ? "within target" : wear >= 3 ? "below the 6-hour adherence target" : "significantly below target";
    sentences.push(`Device worn for ${wear.toFixed(1)} h — ${adequate}.`);
  }

  // Alerts
  if (critical > 0 || warning > 0) {
    const parts = [];
    if (critical > 0) parts.push(`${critical} critical`);
    if (warning  > 0) parts.push(`${warning} warning`);
    sentences.push(`${parts.join(" and ")} alert${parts.length > 1 || (critical + warning) > 1 ? "s are" : " is"} currently open and require clinical review.`);
  } else {
    sentences.push("No alerts are currently active.");
  }

  // Recommendation
  if (score !== null) {
    if (critical > 0 || score < 40) {
      sentences.push("Prompt review of the care plan is recommended.");
    } else if (warning > 0 || score < 60 || scoreTrend === "down") {
      sentences.push("Continue current monitoring; reassess at the next scheduled review.");
    } else {
      sentences.push("Patient is broadly stable. Maintain current monitoring frequency.");
    }
  }

  const assessment = sentences.join(" ");

  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-start justify-between gap-3">
        <div>
          <span className="text-xs font-semibold text-indigo-400 uppercase tracking-widest">
            Clinical Summary
          </span>
          <p className="text-base font-semibold text-gray-100 mt-1">{name}</p>
          <p className="text-xs text-gray-600 mt-0.5">
            ID {patientId} · {todayStr()}
          </p>
        </div>
        <div className="w-9 h-9 rounded-full bg-indigo-400/10 flex items-center justify-center flex-shrink-0 mt-0.5">
          <div className="w-4 h-4 rounded-full bg-indigo-400/30 flex items-center justify-center">
            <div className="w-2 h-2 rounded-full bg-indigo-400" />
          </div>
        </div>
      </div>

      {/* Metrics */}
      <div className="border-t border-gray-800 pt-4">
        <SectionLabel text="Phase 1 Metrics" />
        <div className="mt-2">
          <MetricRow
            label="Independence Score"
            value={fmt(score, (v) => v.toFixed(1))}
            unit="/ 100"
            trendPoints={summary?.trend_independence_score}
            positiveIsGood
          />
          <MetricRow
            label="Wandering Episodes"
            value={fmt(wander, String)}
            unit="ep"
            trendPoints={summary?.trend_wandering_count}
            positiveIsGood={false}
          />
          <MetricRow
            label="Wrong Turns"
            value={fmt(wrong, String)}
            unit=""
            trendPoints={summary?.trend_wrong_turn_count}
            positiveIsGood={false}
          />
          <MetricRow
            label="Movement Radius"
            value={fmt(radius, (v) => Math.round(v).toString())}
            unit="m"
            trendPoints={summary?.trend_movement_radius_m}
            positiveIsGood
          />
          <MetricRow
            label="Wear Hours"
            value={fmt(wear, (v) => v.toFixed(1))}
            unit="h"
            trendPoints={summary?.trend_wear_hours}
            positiveIsGood
          />
          <MetricRow
            label="Fall Events"
            value={fmt(falls, String)}
            unit=""
            trendPoints={null}
            positiveIsGood={false}
          />
        </div>
      </div>

      {/* Active alerts summary */}
      <div>
        <SectionLabel text="Active Alerts" />
        <div className="flex items-center gap-3 mt-2">
          {alerts.length === 0 ? (
            <span className="text-xs text-gray-600">None</span>
          ) : (
            <>
              {critical > 0 && (
                <span className="text-xs px-2.5 py-1 rounded-full bg-red-400/10 text-red-400 font-medium">
                  {critical} critical
                </span>
              )}
              {warning > 0 && (
                <span className="text-xs px-2.5 py-1 rounded-full bg-amber-400/10 text-amber-400 font-medium">
                  {warning} warning
                </span>
              )}
              {alerts.length - critical - warning > 0 && (
                <span className="text-xs px-2.5 py-1 rounded-full bg-blue-400/10 text-blue-400 font-medium">
                  {alerts.length - critical - warning} info
                </span>
              )}
            </>
          )}
        </div>
      </div>

      {/* Assessment paragraph */}
      <div className="border-t border-gray-800 pt-4 mt-auto">
        <SectionLabel text="Assessment" />
        <p className="text-xs text-gray-400 leading-relaxed mt-2">
          {assessment || "No summary data available for this patient."}
        </p>
      </div>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton() {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
      {[0, 1].map((i) => (
        <div key={i} className="bg-gray-900 border border-gray-800 rounded-xl p-6 space-y-5">
          <div className="space-y-2">
            <div className="h-2.5 bg-gray-800 rounded animate-pulse w-24" />
            <div className="h-4 bg-gray-800 rounded animate-pulse w-40" />
            <div className="h-2.5 bg-gray-800 rounded animate-pulse w-32" />
          </div>
          <div className="border-t border-gray-800 pt-4 space-y-2">
            <div className="h-6 bg-gray-800 rounded animate-pulse w-36" />
            <div className="h-2.5 bg-gray-800 rounded animate-pulse w-48" />
          </div>
          <div className="space-y-2.5">
            {[85, 70, 90, 60].map((w, j) => (
              <div key={j} className="flex items-center gap-2.5">
                <div className="w-1.5 h-1.5 rounded-full bg-gray-800 flex-shrink-0" />
                <div className="h-3 bg-gray-800 rounded animate-pulse" style={{ width: `${w}%` }} />
              </div>
            ))}
          </div>
        </div>
      ))}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ReportPreview({ patient, summary, alerts, loading }) {
  if (loading) return <Skeleton />;

  if (!patient && !summary) {
    return (
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        {["Family Update", "Clinical Summary"].map((label) => (
          <div
            key={label}
            className="bg-gray-900 border border-gray-800 rounded-xl p-6 flex items-center justify-center min-h-48"
          >
            <p className="text-xs text-gray-700">{label} — no patient selected</p>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div>
      {/* Section label */}
      <div className="flex items-center gap-3 mb-4">
        <p className="text-xs text-gray-600 uppercase tracking-widest font-medium">
          Report Preview
        </p>
        <div className="flex-1 h-px bg-gray-800" />
        <p className="text-xs text-gray-700">
          {summary ? "Based on 30-day monitoring window" : "Awaiting data"}
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
        <FamilyCard  patient={patient} summary={summary} alerts={alerts} />
        <ClinicalCard patient={patient} summary={summary} alerts={alerts} />
      </div>
    </div>
  );
}
