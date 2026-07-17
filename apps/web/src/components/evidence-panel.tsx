"use client";

import type { EvidenceReport, EvidenceResult } from "@vayu/shared";

import type { Scenario } from "@/lib/scenarios";
import { HYPOTHESIS_LABEL, STRENGTH_LABEL, STRENGTH_STARS } from "@vayu/shared";
import { ChevronDown, ChevronRight } from "lucide-react";
import { useState } from "react";

import { cn } from "@/lib/utils";

/**
 * Evidence for each hypothesis, side by side.
 *
 * Deliberately NOT a pie chart or a stacked bar. Strengths do not sum to 1 —
 * hypotheses are not mutually exclusive, and on a Diwali night in stubble season
 * fire and traffic evidence are both legitimately present. Any chart implying
 * shares would reintroduce the source apportionment the whole system refuses.
 */

const STRENGTH_COLOR: Record<string, string> = {
  very_strong: "text-red-600 dark:text-red-400",
  strong: "text-orange-600 dark:text-orange-400",
  moderate: "text-amber-600 dark:text-amber-400",
  weak: "text-slate-500",
  very_weak: "text-slate-400",
  insufficient_evidence: "text-slate-400",
};

function QualityBadge({ quality }: { quality: string }) {
  const tone =
    quality === "high" || quality === "good"
      ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
      : quality === "fair"
        ? "bg-amber-100 text-amber-800 dark:bg-amber-950 dark:text-amber-300"
        : "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300";
  return (
    <span className={cn("rounded px-1.5 py-0.5 text-[10px] font-medium uppercase", tone)}>
      data {quality.replace("_", " ")}
    </span>
  );
}

function EvidenceRow({ result }: { result: EvidenceResult }) {
  const [open, setOpen] = useState(false);
  const insufficient = result.strength === "insufficient_evidence";

  return (
    <div className="border-b last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-center gap-3 px-4 py-3 text-left transition-colors hover:bg-muted/50"
        aria-expanded={open}
      >
        {open ? (
          <ChevronDown className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        ) : (
          <ChevronRight className="size-4 shrink-0 text-muted-foreground" aria-hidden />
        )}

        <div className="min-w-0 flex-1">
          <div className="flex items-baseline gap-2">
            <span className="font-medium">{HYPOTHESIS_LABEL[result.hypothesis]}</span>
            <QualityBadge quality={result.evidence_quality} />
          </div>
          {insufficient ? (
            <p className="mt-0.5 text-xs text-muted-foreground">
              Cannot judge — required observations unavailable. This is not evidence the source is
              absent.
            </p>
          ) : null}
        </div>

        <div className="shrink-0 text-right">
          <div
            className={cn("font-mono text-lg leading-none", STRENGTH_COLOR[result.strength])}
            title={STRENGTH_LABEL[result.strength]}
          >
            {STRENGTH_STARS[result.strength]}
          </div>
          <div className="mt-1 text-[10px] text-muted-foreground uppercase">
            {STRENGTH_LABEL[result.strength]}
          </div>
        </div>
      </button>

      {open ? (
        <div className="space-y-3 bg-muted/30 px-4 pb-4 pl-11 text-sm">
          <p className="text-muted-foreground">{result.explanation}</p>

          {result.likelihood_ratio !== null ? (
            <p className="text-xs">
              <span className="text-muted-foreground">Likelihood ratio </span>
              <span className="font-mono font-medium">{result.likelihood_ratio.toFixed(2)}</span>
              <span className="text-muted-foreground">
                {" "}
                — Kass &amp; Raftery band. Not a probability.
              </span>
            </p>
          ) : (
            <p className="text-xs text-muted-foreground">
              No likelihood ratio: no natural experiment isolates this hypothesis, so there is
              nothing to calibrate against.
            </p>
          )}

          {result.supporting_observations.length ? (
            <div>
              <p className="mb-1 text-xs font-medium text-emerald-700 dark:text-emerald-400">
                Supporting
              </p>
              <ul className="space-y-0.5">
                {result.supporting_observations.map((o, i) => (
                  <li key={i} className="text-xs text-muted-foreground">
                    + {o.label}
                    {o.value !== null ? (
                      <span className="font-mono text-foreground">
                        {" "}
                        {o.value}
                        {o.unit ? ` ${o.unit}` : ""}
                      </span>
                    ) : null}
                    <span className="text-muted-foreground/60"> ({o.source})</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {result.contradicting_observations.length ? (
            <div>
              <p className="mb-1 text-xs font-medium text-red-700 dark:text-red-400">
                Contradicting
              </p>
              <ul className="space-y-0.5">
                {result.contradicting_observations.map((o, i) => (
                  <li key={i} className="text-xs text-muted-foreground">
                    − {o.label}
                    {o.value !== null ? (
                      <span className="font-mono text-foreground">
                        {" "}
                        {o.value}
                        {o.unit ? ` ${o.unit}` : ""}
                      </span>
                    ) : null}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {result.historical_validation.length ? (
            <div>
              <p className="mb-1 text-xs font-medium text-muted-foreground">
                Historical validation
              </p>
              <ul className="space-y-1">
                {result.historical_validation.map((v, i) => (
                  <li key={i} className="text-xs">
                    <span
                      className={cn(
                        "rounded px-1 py-0.5 text-[10px] font-medium uppercase",
                        v.status === "accepted"
                          ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950 dark:text-emerald-300"
                          : v.status === "rejected"
                            ? "bg-red-100 text-red-800 dark:bg-red-950 dark:text-red-300"
                            : "bg-slate-200 text-slate-700 dark:bg-slate-800 dark:text-slate-300",
                      )}
                    >
                      {v.status}
                    </span>{" "}
                    <span className="font-medium">{v.experiment}</span>
                    <p className="mt-0.5 text-muted-foreground">{v.detail}</p>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
}

export function EvidencePanel({
  report,
  scenario,
}: {
  report: EvidenceReport;
  scenario?: Scenario;
}) {
  return (
    <>
      <header className="flex shrink-0 items-center justify-between border-b border-[#1C1C1C] px-4 py-3">
        <h2 className="text-sm font-medium text-white">Evidence</h2>
        <span className="text-[10px] text-[#71717A]">select to expand</span>
      </header>

      {/* Not a pie chart, and never will be. Strengths do not sum to 1. */}
      <div className="panel-scroll min-h-0 flex-1">
        {scenario && !scenario.complete ? (
          <p className="border-b border-[#1C1C1C] bg-[#111111] px-4 py-2.5 text-[11px] leading-relaxed text-[#EAB308]">
            Fire and weather observations were not collected for this window, so the biomass
            hypothesis cannot be judged. That is a gap in our records, not a finding about the air.
          </p>
        ) : null}
        {report.evidence.map((r) => (
          <EvidenceRow key={r.name} result={r} />
        ))}
      </div>

      <footer className="shrink-0 border-t border-[#1C1C1C] px-4 py-2 text-[10px] leading-relaxed text-[#71717A]">
        Evidence for independent explanations. These do not sum to 100% and are not source shares.
      </footer>
    </>
  );
}
