"use client";

import type { DecisionReport, EvidenceReport } from "@vayu/shared";

import { cn } from "@/lib/utils";

/**
 * The first thing an officer sees: what is happening, right now, in words.
 *
 * Severity is derived from the measured PM2.5 against CPCB's published AQI
 * breakpoints — a measured concentration compared to a published threshold, which
 * is defensible. It is NOT derived from the evidence, because evidence strength
 * says which hypothesis is plausible, not how bad the air is.
 */

// CPCB PM2.5 sub-index breakpoints (µg/m³, 24h). Used here on an hourly value,
// which overstates the official category — hence "concentration", not "AQI".
const BANDS: Array<{ max: number; label: string; tone: string }> = [
  { max: 30, label: "Good", tone: "bg-emerald-600" },
  { max: 60, label: "Satisfactory", tone: "bg-lime-600" },
  { max: 90, label: "Moderate", tone: "bg-yellow-500" },
  { max: 120, label: "Poor", tone: "bg-orange-500" },
  { max: 250, label: "Very Poor", tone: "bg-red-600" },
  { max: Infinity, label: "Severe", tone: "bg-red-900" },
];

function band(pm25: number) {
  return BANDS.find((b) => pm25 <= b.max) ?? BANDS[BANDS.length - 1];
}

export function SituationHeader({
  evidence,
  decision,
}: {
  evidence: EvidenceReport;
  decision: DecisionReport;
}) {
  const pm25 = evidence.measured_pm25;
  const b = pm25 !== null ? band(pm25) : null;

  const when = new Date(evidence.evaluated_at).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    dateStyle: "medium",
    timeStyle: "short",
  });

  return (
    <section className="rounded-lg border bg-card">
      <div className="flex flex-wrap items-start justify-between gap-4 p-4">
        <div>
          <p className="text-xs text-muted-foreground uppercase">Current situation</p>
          <div className="mt-1 flex items-center gap-3">
            {b ? (
              <span className={cn("rounded px-2.5 py-1 text-lg font-semibold text-white", b.tone)}>
                {b.label}
              </span>
            ) : (
              <span className="rounded bg-muted px-2.5 py-1 text-lg font-semibold">Unknown</span>
            )}
            {pm25 !== null ? (
              <span className="font-mono text-2xl font-semibold">
                {pm25.toFixed(0)}
                <span className="ml-1 text-sm font-normal text-muted-foreground">µg/m³ PM2.5</span>
              </span>
            ) : null}
          </div>
          <p className="mt-1.5 text-sm text-muted-foreground">
            {evidence.station} · {when} IST
          </p>
        </div>

        <div className="text-right">
          <p className="text-xs text-muted-foreground uppercase">Status</p>
          <p className="mt-1 font-medium capitalize">
            {decision.overall_status.replace(/_/g, " ")}
          </p>
          <p className="mt-0.5 text-xs text-muted-foreground">
            data quality: {decision.data_quality.replace("_", " ")}
          </p>
        </div>
      </div>

      <p className="border-t px-4 py-2 text-[11px] text-muted-foreground">
        Severity is the measured concentration against CPCB PM2.5 breakpoints. Applied to an hourly
        value, so it reads more severe than the official 24-hour AQI category.
      </p>
    </section>
  );
}
