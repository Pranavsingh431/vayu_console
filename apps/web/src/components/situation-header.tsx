"use client";

import type { DecisionReport, EvidenceReport } from "@vayu/shared";
import { History } from "lucide-react";

import type { Scenario } from "@/lib/scenarios";
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

/**
 * Every scenario in this console is a reconstruction of a past incident, and the
 * screen must say so before it says anything else.
 *
 * Without this strip the console reads as a live feed: a judge sees "Severe,
 * 1288 µg/m³, human review required" and has no reason to think otherwise. The
 * date alone is not enough — operational dashboards routinely show a timestamp
 * for a reading that is current. So the strip names the mode, not just the time.
 */
export function ReplayBanner({
  scenario,
  evidence,
}: {
  scenario: Scenario;
  evidence: EvidenceReport;
}) {
  const when = new Date(evidence.evaluated_at).toLocaleString("en-IN", {
    timeZone: "Asia/Kolkata",
    day: "2-digit",
    month: "short",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  });

  return (
    <div className="flex shrink-0 items-center gap-3 border-b border-[#1C1C1C] bg-[#111111] px-6 py-1.5">
      <History className="size-3 shrink-0 text-[#EAB308]" aria-hidden />
      <span className="text-[10px] font-medium tracking-[0.2em] text-[#EAB308] uppercase">
        Historical replay
      </span>
      <span className="text-[#3F3F46]" aria-hidden>
        ·
      </span>
      <span className="text-[11px] font-medium text-white">{scenario.label}</span>
      <span className="text-[#3F3F46]" aria-hidden>
        ·
      </span>
      <span className="font-mono text-[11px] text-[#A1A1AA]">{when} IST</span>
      <span className="ml-auto hidden text-[10px] text-[#71717A] lg:block">
        Reconstructed from archived observations. Not a live feed.
      </span>
    </div>
  );
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
          <p className="text-[10px] tracking-wider text-[#71717A] uppercase">Incident situation</p>
          <div className="mt-0.5 flex items-baseline gap-3">
            <span
              className={cn("text-2xl font-semibold tracking-tight", b?.tone ?? "text-[#A1A1AA]")}
            >
              {b?.label ?? "Not measured"}
            </span>
            {pm25 !== null ? (
              <span className="font-mono text-xl font-medium text-white">
                {pm25.toFixed(0)}
                <span className="ml-1.5 font-sans text-[10px] font-normal text-[#71717A]">
                  µg/m³ observed PM2.5
                </span>
              </span>
            ) : (
              <span className="text-[11px] text-[#71717A]">
                No PM2.5 reading at this station-hour
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="ml-auto grid flex-1 grid-cols-2 gap-x-8 gap-y-2 lg:grid-cols-4">
        <Stat label="Station">{evidence.station.split(",")[0]}</Stat>
        <Stat label="Observed at (IST)">{when}</Stat>
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

      {/* "Updated" would read as data freshness on a live feed. This is when the
          engines last ran over the archived observations, which is a different
          claim. */}
      <p className="hidden font-mono text-[10px] whitespace-nowrap text-[#71717A] xl:block">
        analysed {generated}
      </p>
    </header>
  );
}
