/**
 * ClinicalSummary — narrative clinical interpretation panel.
 *
 * Props:
 *   summary   object|null   from GET /patients/:id/summary
 *   loading   boolean
 *
 * Converts numeric summary fields into plain-language clinical observations
 * and produces a short overall assessment paragraph from combined signals.
 *
 * Summary fields used:
 *   latest_independence_score, latest_wandering_count, latest_wrong_turn_count,
 *   latest_movement_radius_m, latest_wear_hours, latest_fall_count,
 *   trend_independence_score, trend_wandering_count, trend_wear_hours,
 *   trend_movement_radius_m
 */

// ── Level config ──────────────────────────────────────────────────────────────

const LEVEL = {
  ok:       { dot: "bg-green-400",  text: "text-green-400"  },
  warn:     { dot: "bg-amber-400",  text: "text-amber-400"  },
  critical: { dot: "bg-red-400",    text: "text-red-400"    },
  neutral:  { dot: "bg-gray-700",   text: "text-gray-600"   },
};

// ── Trend helper ──────────────────────────────────────────────────────────────

/**
 * Compare the mean of the last 7 non-null values vs the 7 before that.
 * Returns "up" | "down" | "stable" | null.
 */
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

// ── Metric interpreters ───────────────────────────────────────────────────────
// Each returns { text: string, level: "ok"|"warn"|"critical"|"neutral" }.

function interpretScore(value, trend) {
  if (value === null || value === undefined)
    return { text: "Independence score not yet available.", level: "neutral" };

  const dir =
    trend === "up"   ? " — improving trend."  :
    trend === "down" ? " — declining trend."  : ".";

  if (value >= 70)
    return { text: `Score of ${value.toFixed(1)} indicates maintained independence${dir}`, level: "ok" };
  if (value >= 50)
    return { text: `Score of ${value.toFixed(1)} is moderately reduced; continued monitoring recommended${dir}`, level: "warn" };
  if (value >= 40)
    return { text: `Score of ${value.toFixed(1)} is below the warning threshold — care plan review advised${dir}`, level: "warn" };
  return { text: `Score of ${value.toFixed(1)} is critically low — immediate clinical review advised${dir}`, level: "critical" };
}

function interpretWandering(count, trend) {
  if (count === null || count === undefined)
    return { text: "Wandering data unavailable for this period.", level: "neutral" };

  const dir =
    trend === "up"   ? " Frequency has been rising."     :
    trend === "down" ? " Frequency has been decreasing." : "";

  if (count === 0)
    return { text: `No wandering episodes recorded.${dir}`,                                              level: "ok"       };
  if (count === 1)
    return { text: `One episode recorded — within manageable range.${dir}`,                              level: "ok"       };
  if (count <= 3)
    return { text: `${count} episodes noted; caregiver awareness recommended.${dir}`,                    level: "warn"     };
  return   { text: `${count} episodes — elevated frequency; environmental safety review suggested.${dir}`, level: "critical" };
}

function interpretWrongTurns(count) {
  if (count === null || count === undefined)
    return { text: "Navigation data unavailable.", level: "neutral" };

  if (count === 0)
    return { text: "No navigation errors recorded.",                                                     level: "ok"       };
  if (count === 1)
    return { text: "One wrong turn recorded — may reflect transient disorientation.",                    level: "warn"     };
  if (count <= 3)
    return { text: `${count} wrong turns suggest repeated spatial orientation difficulty.`,               level: "warn"     };
  return   { text: `${count} wrong turns indicate significant spatial disorientation risk.`,              level: "critical" };
}

function interpretRadius(metres, trend) {
  if (metres === null || metres === undefined)
    return { text: "Movement radius data unavailable.", level: "neutral" };

  const m   = Math.round(metres);
  const dir =
    trend === "up"   ? " Range is expanding."    :
    trend === "down" ? " Range is contracting."  : "";

  if (m > 500)
    return { text: `Radius of ${m} m — healthy community-level mobility.${dir}`,             level: "ok"       };
  if (m > 200)
    return { text: `Radius of ${m} m — patient mobile within the neighbourhood.${dir}`,      level: "ok"       };
  if (m > 50)
    return { text: `Radius of ${m} m — activity largely confined to the home area.${dir}`,   level: "warn"     };
  return   { text: `Radius of ${m} m — patient is near-homebound.${dir}`,                    level: "critical" };
}

function interpretWear(hours, trend) {
  if (hours === null || hours === undefined)
    return { text: "Wear adherence data unavailable.", level: "neutral" };

  const h   = hours.toFixed(1);
  const dir =
    trend === "up"   ? " Adherence has been improving." :
    trend === "down" ? " Adherence has been declining." : "";

  if (hours >= 6)
    return { text: `${h} h worn — monitoring data is comprehensive.${dir}`,                   level: "ok"       };
  if (hours >= 4)
    return { text: `${h} h worn — minor monitoring gaps possible.${dir}`,                     level: "warn"     };
  if (hours >= 2)
    return { text: `${h} h worn — below target; some periods may be unmonitored.${dir}`,      level: "warn"     };
  return   { text: `${h} h worn — very low wear; data reliability is limited.${dir}`,         level: "critical" };
}

function interpretFalls(count) {
  if (count === null || count === undefined)
    return { text: "Fall data unavailable.", level: "neutral" };

  if (count === 0) return { text: "No falls recorded in the monitored period.",                      level: "ok"       };
  if (count === 1) return { text: "One fall detected — fall risk assessment recommended.",            level: "warn"     };
  return           { text: `${count} falls detected — urgent fall risk intervention advised.`,        level: "critical" };
}

// ── Overall assessment ────────────────────────────────────────────────────────

function overallAssessment(items) {
  const levels    = items.map((i) => i.level).filter((l) => l !== "neutral");
  const nCritical = levels.filter((l) => l === "critical").length;
  const nWarn     = levels.filter((l) => l === "warn").length;

  if (nCritical >= 2)
    return "Multiple critical indicators are present. Prompt clinical review and coordinated caregiver intervention are recommended. Reassess the patient's safety plan with the care team.";
  if (nCritical === 1)
    return "One critical indicator requires attention. Review the flagged metric with the care team and consider adjusting the current monitoring or care arrangements accordingly.";
  if (nWarn >= 3)
    return "Several metrics are below target. While no single critical concern is present, the overall pattern warrants a proactive care team review before the next scheduled appointment.";
  if (nWarn >= 1)
    return "Patient is broadly stable with some metrics requiring ongoing monitoring. Continue the current care plan and reassess at the next scheduled review.";
  return "All monitored metrics are within expected ranges. Patient appears stable across independence, mobility, adherence, and safety indicators. Maintain current monitoring frequency.";
}

// ── Observation row ───────────────────────────────────────────────────────────

function ObsRow({ label, interpretation }) {
  const { text, level } = interpretation;
  const cfg = LEVEL[level] ?? LEVEL.neutral;

  return (
    <div className="flex items-start gap-2.5">
      <span className={`w-1.5 h-1.5 rounded-full flex-shrink-0 mt-1 ${cfg.dot}`} />
      <div className="min-w-0">
        <p className="text-xs text-gray-600 uppercase tracking-widest leading-none mb-1">
          {label}
        </p>
        <p className={`text-xs leading-relaxed ${level === "neutral" ? "text-gray-600" : "text-gray-300"}`}>
          {text}
        </p>
      </div>
    </div>
  );
}

// ── Skeleton ──────────────────────────────────────────────────────────────────

function Skeleton() {
  const rows = [80, 64, 72, 56, 68, 60];
  return (
    <div className="space-y-4">
      {rows.map((w, i) => (
        <div key={i} className="flex items-start gap-2.5">
          <div className="w-1.5 h-1.5 rounded-full bg-gray-800 flex-shrink-0 mt-1" />
          <div className="flex-1 space-y-1.5">
            <div className="h-2 bg-gray-800 rounded animate-pulse w-20" />
            <div className="h-3 bg-gray-800 rounded animate-pulse" style={{ width: `${w}%` }} />
          </div>
        </div>
      ))}
      <div className="border-t border-gray-800 pt-4 space-y-1.5">
        <div className="h-2 bg-gray-800 rounded animate-pulse w-32" />
        <div className="h-3 bg-gray-800 rounded animate-pulse w-full" />
        <div className="h-3 bg-gray-800 rounded animate-pulse w-5/6" />
        <div className="h-3 bg-gray-800 rounded animate-pulse w-3/4" />
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function ClinicalSummary({ summary, loading }) {
  return (
    <div className="bg-gray-900 border border-gray-800 rounded-xl p-5 flex flex-col gap-4">
      {/* Header */}
      <p className="text-xs text-gray-500 flex-shrink-0">Clinical Summary</p>

      {loading ? (
        <Skeleton />
      ) : !summary ? (
        <p className="text-xs text-gray-700 py-6 text-center">No summary data available.</p>
      ) : (() => {
          const scoreTrend  = trendDir(summary.trend_independence_score);
          const wanderTrend = trendDir(summary.trend_wandering_count);
          const wearTrend   = trendDir(summary.trend_wear_hours);
          const radiusTrend = trendDir(summary.trend_movement_radius_m);

          const observations = [
            { label: "Independence Score",  interp: interpretScore(summary.latest_independence_score, scoreTrend)  },
            { label: "Wandering Pattern",   interp: interpretWandering(summary.latest_wandering_count, wanderTrend) },
            { label: "Wrong-Turn Pattern",  interp: interpretWrongTurns(summary.latest_wrong_turn_count)           },
            { label: "Movement Radius",     interp: interpretRadius(summary.latest_movement_radius_m, radiusTrend) },
            { label: "Wear Adherence",      interp: interpretWear(summary.latest_wear_hours, wearTrend)            },
            { label: "Fall Observation",    interp: interpretFalls(summary.latest_fall_count)                      },
          ];

          const assessment = overallAssessment(observations.map((o) => o.interp));

          return (
            <>
              {/* Observations */}
              <div className="space-y-3.5">
                {observations.map(({ label, interp }) => (
                  <ObsRow key={label} label={label} interpretation={interp} />
                ))}
              </div>

              {/* Overall assessment */}
              <div className="border-t border-gray-800 pt-4">
                <p className="text-xs text-gray-600 uppercase tracking-widest mb-2">
                  Overall Assessment
                </p>
                <p className="text-xs text-gray-400 leading-relaxed">
                  {assessment}
                </p>
              </div>
            </>
          );
        })()
      }
    </div>
  );
}
