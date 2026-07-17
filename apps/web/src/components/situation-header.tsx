"use client";

import type { DecisionReport, EvidenceReport } from "@vayu/shared";

import { cn } from "@/lib/utils";

/**
 * The first thing on screen, and the only thing a judge is guaranteed to read.
 *
 * Severity comes from the measured concentration against CPCB's published PM2.5
 * breakpoints — a measured number against a published threshold, which an officer
 * can cite. Deliberately NOT derived from evidence strength: evidence says which
 * explanation is plausible, not how bad the air is.
 */

const BANDS = [
  { max: 30, label: "Good", tone: "text-[#22C55E]", bar: "bg-[#22C55E]" },
  { max: 60, label: "Satisfactory", tone: "text-[#22C55E]", bar: "bg-[#22C55E]" },
  { max: 90, label: "Moderate", tone: "text-[#EAB308]", bar: "bg-[#EAB308]" },
  { max: 120, label: "Poor", tone: "text-[#EAB308]", bar: "bg-[#EAB308]" },
  { max: 250, label: "Very Poor", tone: "text-[#EF4444]", bar: "bg-[#EF4444]" },
  { max: Infinity, label: "Severe", tone: "text-[#EF4444]", bar: "bg-[#EF4444]" },
];

function band(pm25: number) {
  return BANDS.find((b) => pm25 <= b.max) ?? BANDS[BANDS.length - 1];
}

function Stat({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <p className="text-[10px] tracking-wider text-[#71717A] uppercase">{label}</p>
      <div className="mt-1 truncate text-sm text-white">{children}</div>
    </div>
  );
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
  const generated = new Date(decision.generated_at).toLocaleTimeString("en-IN", {
    timeZone: "Asia/Kolkata",
    timeStyle: "medium",
  });

  return (
    <header className="flex items-center gap-8 border-b border-[#1C1C1C] bg-[#0A0A0A] px-6 py-3.5">
      {/* The number. Everything else on this bar is context for it. */}
      <div className="flex items-center gap-4">
        <div className={cn("h-12 w-1 rounded-full", b?.bar ?? "bg-[#1C1C1C]")} aria-hidden />
        <div>
          <p className="text-[10px] tracking-wider text-[#71717A] uppercase">Situation</p>
          <div className="mt-0.5 flex items-baseline gap-3">
            <span
              className={cn("text-2xl font-semibold tracking-tight", b?.tone ?? "text-[#A1A1AA]")}
            >
              {b?.label ?? "Unknown"}
            </span>
            {pm25 !== null ? (
              <span className="font-mono text-xl font-medium text-white">
                {pm25.toFixed(0)}
                <span className="ml-1.5 text-[10px] font-normal text-[#71717A]">µg/m³ PM2.5</span>
              </span>
            ) : null}
          </div>
        </div>
      </div>

      <div className="ml-auto grid flex-1 grid-cols-2 gap-x-8 gap-y-2 lg:grid-cols-4">
        <Stat label="Location">{evidence.station.split(",")[0]}</Stat>
        <Stat label="Time (IST)">{when}</Stat>
        <Stat label="Status">
          <span className="capitalize">{decision.overall_status.replace(/_/g, " ")}</span>
        </Stat>
        <Stat label="Review">
          {decision.requires_human_review ? (
            <span className="text-[#EAB308]">Human review required</span>
          ) : (
            <span className="text-[#22C55E]">Cleared</span>
          )}
        </Stat>
      </div>

      <p className="hidden font-mono text-[10px] whitespace-nowrap text-[#71717A] xl:block">
        updated {generated}
      </p>
    </header>
  );
}
