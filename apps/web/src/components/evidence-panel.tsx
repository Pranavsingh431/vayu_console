"use client";

import type { EvidenceReport, EvidenceResult } from "@vayu/shared";

import type { Scenario } from "@/lib/scenarios";
import type { EvidenceQuality } from "@vayu/shared";
import { HYPOTHESIS_LABEL, QUALITY_LABEL, STRENGTH_LABEL, STRENGTH_STARS } from "@vayu/shared";
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
 *
 * Colours come from the four-value operations palette in `globals.css`, never
 * from Tailwind's light/dark pairs: this product has no light mode, and a
 * `dark:` utility silently resolves against the visitor's OS setting rather than
 * against the theme. On a laptop set to light mode that rendered pale pastel
 * chips on pure black.
 */

const STRENGTH_COLOR: Record<string, string> = {
  very_strong: "text-[#EF4444]",
  strong: "text-[#EF4444]",
  moderate: "text-[#EAB308]",
  weak: "text-[#A1A1AA]",
  very_weak: "text-[#71717A]",
  insufficient_evidence: "text-[#52525B]",
};

/**
 * Data quality, stated as words.
 *
 * Quality describes the observations, not the conclusion, so it stays visually
 * quieter than the strength rating beside it — a bordered chip rather than a
 * filled one. Only `no_data` earns colour, because that is the case an officer
 * must not read past.
 */
function QualityBadge({ quality }: { quality: EvidenceQuality }) {
  const tone =
    quality === "no_data"
      ? "border-[#EF4444]/40 text-[#EF4444]"
      : quality === "poor" || quality === "fair"
        ? "border-[#EAB308]/40 text-[#EAB308]"
        : "border-[#1C1C1C] text-[#71717A]";
  return (
    <span
      className={cn(
        "shrink-0 rounded border px-1.5 py-0.5 text-[10px] font-medium whitespace-nowrap uppercase",
        tone,
      )}
    >
      {QUALITY_LABEL[quality]}
    </span>
  );
}

function EvidenceRow({ result }: { result: EvidenceResult }) {
  const [open, setOpen] = useState(false);
  const insufficient = result.strength === "insufficient_evidence";

  return (
    <div className="border-b border-[#1C1C1C] last:border-b-0">
      <button
        onClick={() => setOpen(!open)}
        className="flex w-full items-start gap-2.5 px-4 py-3 text-left transition-colors duration-150 hover:bg-[#111111]"
        aria-expanded={open}
      >
        {open ? (
          <ChevronDown className="mt-0.5 size-4 shrink-0 text-[#71717A]" aria-hidden />
        ) : (
          <ChevronRight className="mt-0.5 size-4 shrink-0 text-[#71717A]" aria-hidden />
        )}

        <div className="min-w-0 flex-1">
          {/* Hypothesis and rating on one line, so the eye compares ratings down
              the column rather than hunting for them. */}
          <div className="flex items-baseline justify-between gap-3">
            <span className="truncate font-medium text-white">
              {HYPOTHESIS_LABEL[result.hypothesis]}
            </span>
            <span
              className={cn(
                "shrink-0 font-mono text-sm leading-none",
                STRENGTH_COLOR[result.strength],
              )}
              title={STRENGTH_LABEL[result.strength]}
            >
              {STRENGTH_STARS[result.strength]}
            </span>
          </div>

          <div className="mt-1.5 flex flex-wrap items-center gap-1.5">
            <span
              className={cn(
                "text-[10px] tracking-wider uppercase",
                insufficient ? "text-[#EF4444]" : "text-[#71717A]",
              )}
            >
              {insufficient ? "Insufficient evidence" : STRENGTH_LABEL[result.strength]}
            </span>
            <span className="text-[#3F3F46]" aria-hidden>
              ·
            </span>
            <QualityBadge quality={result.evidence_quality} />
          </div>

          {insufficient ? (
            <p className="mt-1.5 text-[11px] leading-relaxed text-[#A1A1AA]">
              Required observations are unavailable for this window, so no conclusion is drawn. This
              is not evidence that the source is absent.
            </p>
          ) : null}
        </div>
      </button>

      {open ? (
        <div className="space-y-3 border-t border-[#1C1C1C] bg-[#050505] px-4 pb-4 pl-11 text-sm">
          <p className="pt-3 text-xs leading-relaxed text-[#A1A1AA]">{result.explanation}</p>

          {result.likelihood_ratio !== null ? (
            <p className="text-xs">
              <span className="text-[#71717A]">Likelihood ratio </span>
              <span className="font-mono font-medium text-white">
                {result.likelihood_ratio.toFixed(2)}
              </span>
              <span className="text-[#71717A]"> — Kass &amp; Raftery band. Not a probability.</span>
            </p>
          ) : (
            <p className="text-xs text-[#71717A]">
              No likelihood ratio: no natural experiment isolates this hypothesis, so there is
              nothing to calibrate against.
            </p>
          )}

          {result.supporting_observations.length ? (
            <div>
              <p className="mb-1 text-[10px] font-medium tracking-wider text-[#22C55E] uppercase">
                Supporting
              </p>
              <ul className="space-y-0.5">
                {result.supporting_observations.map((o, i) => (
                  <li key={i} className="text-xs text-[#A1A1AA]">
                    + {o.label}
                    {o.value !== null ? (
                      <span className="font-mono text-white">
                        {" "}
                        {o.value}
                        {o.unit ? ` ${o.unit}` : ""}
                      </span>
                    ) : null}
                    <span className="text-[#52525B]"> ({o.source})</span>
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {result.contradicting_observations.length ? (
            <div>
              <p className="mb-1 text-[10px] font-medium tracking-wider text-[#EF4444] uppercase">
                Contradicting
              </p>
              <ul className="space-y-0.5">
                {result.contradicting_observations.map((o, i) => (
                  <li key={i} className="text-xs text-[#A1A1AA]">
                    − {o.label}
                    {o.value !== null ? (
                      <span className="font-mono text-white">
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
              <p className="mb-1 text-[10px] font-medium tracking-wider text-[#71717A] uppercase">
                Historical validation
              </p>
              <ul className="space-y-1">
                {result.historical_validation.map((v, i) => (
                  <li key={i} className="text-xs">
                    <span
                      className={cn(
                        "rounded px-1 py-0.5 text-[10px] font-medium uppercase",
                        v.status === "accepted"
                          ? "bg-[#22C55E] text-black"
                          : v.status === "rejected"
                            ? "bg-[#EF4444] text-white"
                            : "bg-[#27272A] text-[#A1A1AA]",
                      )}
                    >
                      {v.status}
                    </span>{" "}
                    <span className="font-medium text-white">{v.experiment}</span>
                    <p className="mt-0.5 text-[#71717A]">{v.detail}</p>
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
