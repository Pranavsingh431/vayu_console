"use client";

import type { DecisionReport, Priority, Recommendation } from "@vayu/shared";
import { AlertTriangle, ArrowRight, ShieldQuestion, X } from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Recommendations, and the Challenge affordance.
 *
 * The Challenge dialog is the point of the product. It shows the officer exactly
 * what the advice rests on, what argues against it, and which assumptions must
 * hold — everything they need to defend it in a meeting, or abandon it.
 *
 * Colours come from the operations palette in `globals.css`. No `dark:` pairs:
 * this product has no light mode, and those resolve against the visitor's OS
 * setting rather than the theme.
 */

const PRIORITY_TONE: Record<Priority, string> = {
  immediate: "bg-[#EF4444] text-white",
  high: "bg-[#EAB308] text-black",
  routine: "bg-[#27272A] text-[#A1A1AA]",
  informational: "bg-[#1C1C1C] text-[#71717A]",
};

/**
 * The audit trace, full screen height, scrolling inside itself.
 *
 * Keyboard behaviour is not decoration here. This dialog is opened in front of
 * judges, sometimes by Presentation Mode rather than by a click, so Escape must
 * always close it and focus must not be left on the button underneath — a
 * screen-reader user would otherwise be reading the page behind the overlay.
 */
function ChallengeDialog({
  recommendation,
  onClose,
}: {
  recommendation: Recommendation;
  onClose: () => void;
}) {
  const r = recommendation;
  const panel = useRef<HTMLDivElement>(null);
  const restoreTo = useRef<HTMLElement | null>(null);

  // Move focus in on open, and put it back where it came from on close.
  useEffect(() => {
    restoreTo.current = document.activeElement as HTMLElement | null;
    panel.current?.focus();
    return () => restoreTo.current?.focus?.();
  }, []);

  const onKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        e.stopPropagation();
        onClose();
        return;
      }
      if (e.key !== "Tab" || !panel.current) return;

      // Cycle focus within the dialog rather than escaping to the page behind.
      const focusable = panel.current.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])',
      );
      if (!focusable.length) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      const active = document.activeElement;

      if (e.shiftKey && (active === first || active === panel.current)) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && active === last) {
        e.preventDefault();
        first.focus();
      }
    },
    [onClose],
  );

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/80 p-4 sm:p-8"
      onClick={onClose}
    >
      <div
        ref={panel}
        role="dialog"
        aria-modal="true"
        aria-label={`Why this recommendation: ${r.title}`}
        tabIndex={-1}
        onKeyDown={onKeyDown}
        // max-h + internal scroll: the trace is long, and a dialog taller than
        // the viewport hides its own close button on a laptop screen.
        // focus-visible:ring-0 — the panel takes focus on open so the keyboard
        // lands inside the dialog, but it is a container, not a control, and the
        // global focus ring around the whole modal reads as an error state.
        className="flex max-h-full w-full max-w-3xl flex-col overflow-hidden rounded-md border border-[#1C1C1C] bg-[#0A0A0A] shadow-2xl outline-none focus-visible:ring-0 focus-visible:ring-offset-0"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex shrink-0 items-start justify-between gap-4 border-b border-[#1C1C1C] px-5 py-4">
          <div>
            <p className="text-[10px] tracking-wider text-[#71717A] uppercase">
              Why this recommendation?
            </p>
            <h3 className="mt-1 text-lg font-semibold text-white">{r.title}</h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="rounded p-1 text-[#71717A] transition-colors duration-150 hover:bg-[#1C1C1C] hover:text-white"
          >
            <X className="size-5" />
          </button>
        </header>

        <div className="panel-scroll min-h-0 flex-1 space-y-5 px-5 py-4 text-sm">
          {/* The trace is the spine of the whole feature: advice back to observation. */}
          <div>
            <p className="mb-2 text-[10px] font-medium tracking-wider text-[#71717A] uppercase">
              Decision trace
            </p>
            <ol className="space-y-2">
              {r.decision_trace.map((t, i) => (
                <li key={i} className="flex gap-3">
                  <span className="w-24 shrink-0 pt-1 text-[10px] font-medium tracking-wider text-[#52525B] uppercase">
                    {t.step}
                  </span>
                  <div className="min-w-0 flex-1">
                    <span className="rounded bg-[#1C1C1C] px-1.5 py-0.5 font-mono text-xs text-white">
                      {t.identifier}
                    </span>
                    <p className="mt-1 text-xs leading-relaxed text-[#A1A1AA]">{t.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-1.5 text-[10px] font-medium tracking-wider text-[#22C55E] uppercase">
                Supporting evidence
              </p>
              {r.supporting_evidence.length ? (
                <ul className="space-y-1">
                  {r.supporting_evidence.map((o, i) => (
                    <li key={i} className="text-xs text-[#A1A1AA]">
                      + {o.label}
                      {o.value !== null ? (
                        <span className="font-mono text-white"> {o.value}</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-[#71717A]">None recorded.</p>
              )}
            </div>

            {/* Never hidden. The officer needs the counter-argument before
                someone else in the meeting supplies it. */}
            <div>
              <p className="mb-1.5 text-[10px] font-medium tracking-wider text-[#EF4444] uppercase">
                Contradicting evidence
              </p>
              {r.contradicting_evidence.length ? (
                <ul className="space-y-1">
                  {r.contradicting_evidence.map((o, i) => (
                    <li key={i} className="text-xs text-[#A1A1AA]">
                      − {o.label}
                      {o.value !== null ? (
                        <span className="font-mono text-white"> {o.value}</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-[#71717A]">None recorded.</p>
              )}
            </div>
          </div>

          <div className="rounded-md border border-[#1C1C1C] bg-[#111111] p-3">
            <p className="mb-1 text-[10px] font-medium tracking-wider text-[#71717A] uppercase">
              How far this can be pushed
            </p>
            <p className="text-xs leading-relaxed text-[#A1A1AA]">{r.confidence_note}</p>
          </div>

          {r.assumptions.length ? (
            <div>
              <p className="mb-1.5 text-[10px] font-medium tracking-wider text-[#71717A] uppercase">
                Assumptions
              </p>
              <ul className="space-y-1">
                {r.assumptions.map((a, i) => (
                  <li key={i} className="text-xs leading-relaxed text-[#A1A1AA]">
                    • {a}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {r.limitations.length ? (
            <div>
              <p className="mb-1.5 text-[10px] font-medium tracking-wider text-[#71717A] uppercase">
                Limitations
              </p>
              <ul className="space-y-1">
                {r.limitations.map((l, i) => (
                  <li key={i} className="text-xs leading-relaxed text-[#A1A1AA]">
                    • {l}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="rounded-md border-l-2 border-[#EAB308] bg-[#111111] p-3">
            <p className="text-xs leading-relaxed text-[#A1A1AA]">
              <span className="font-medium text-white">To challenge this:</span> check the
              contradicting evidence and the assumptions first. If an assumption does not hold at
              this station, the recommendation does not follow.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}

function ExpectedImpact({ report }: { report: DecisionReport }) {
  const fireDriven = report.recommendations.some((r) => r.triggered_by_rule.startsWith("FIRE"));
  if (!report.recommendations.length) return null;

  return (
    <div className="shrink-0 border-t border-[#1C1C1C] px-4 py-3">
      <p className="mb-1 text-[10px] font-medium tracking-wider text-[#71717A] uppercase">
        Expected impact
      </p>
      {fireDriven ? (
        <p className="text-xs leading-relaxed text-[#A1A1AA]">
          If upwind fire activity declines, air quality is expected to improve.{" "}
          <span className="font-medium text-white">Reassess within 6 hours.</span> Reason: the
          recommendation rests on transient fire evidence — satellite detections from the last 24
          hours, which will have moved on.
        </p>
      ) : (
        <p className="text-xs leading-relaxed text-[#A1A1AA]">
          <span className="font-medium text-white">Reassess at the next commute peak.</span> Reason:
          the recommendation rests on traffic evidence, which follows a daily cycle rather than a
          weather event.
        </p>
      )}
      <p className="mt-1.5 text-[10px] leading-relaxed text-[#71717A]">
        Qualitative guidance only. The system does not forecast concentrations and cannot estimate
        the effect of any action.
      </p>
    </div>
  );
}

export function RecommendationPanel({
  report,
  autoOpenChallenge = false,
  onChallengeClose,
}: {
  report: DecisionReport;
  autoOpenChallenge?: boolean;
  onChallengeClose?: () => void;
}) {
  const [challenging, setChallenging] = useState<Recommendation | null>(null);

  // Presentation Mode opens the first recommendation's Challenge on its own —
  // the step that shows judges the reasoning rather than describing it.
  useEffect(() => {
    if (autoOpenChallenge && report.recommendations.length) {
      setChallenging(report.recommendations[0]);
    } else if (!autoOpenChallenge) {
      setChallenging(null);
    }
  }, [autoOpenChallenge, report.recommendations]);

  const close = () => {
    setChallenging(null);
    onChallengeClose?.();
  };

  return (
    <>
      <header className="flex shrink-0 items-center justify-between border-b border-[#1C1C1C] px-4 py-3">
        <h2 className="text-sm font-medium text-white">Recommended action</h2>
        {report.requires_human_review ? (
          <span className="flex items-center gap-1 rounded border border-[#EAB308]/40 px-2 py-0.5 text-[10px] font-medium tracking-wider text-[#EAB308] uppercase">
            <AlertTriangle className="size-3" aria-hidden />
            human review
          </span>
        ) : null}
      </header>

      {/* One scroll region for the whole body. Pinning the caveats to the panel
          floor squeezed the recommendation list until only the first of two was
          visible — and the recommendations are what the officer came for. */}
      <div className="panel-scroll min-h-0 flex-1">
        {report.conflict_note ? (
          <div className="border-b border-l-2 border-[#1C1C1C] border-l-[#EAB308] bg-[#111111] px-4 py-2.5">
            <p className="text-xs leading-relaxed text-[#A1A1AA]">{report.conflict_note}</p>
          </div>
        ) : null}

        {report.recommendations.length === 0 ? (
          <div className="px-4 py-6">
            <p className="text-sm font-medium text-white">
              {report.overall_status === "insufficient_evidence"
                ? "No recommendation can be justified."
                : "No action recommended."}
            </p>
            <p className="mt-1.5 text-xs leading-relaxed text-[#A1A1AA]">{report.summary}</p>
          </div>
        ) : (
          <ul>
            {report.recommendations.map((r) => (
              <li key={r.id} className="border-b border-[#1C1C1C] px-4 py-3 last:border-b-0">
                <div className="flex items-start justify-between gap-3">
                  <div className="min-w-0">
                    <div className="flex items-center gap-2">
                      <span
                        className={cn(
                          "rounded px-1.5 py-0.5 text-[10px] font-medium uppercase",
                          PRIORITY_TONE[r.priority],
                        )}
                      >
                        {r.priority}
                      </span>
                      <span className="text-[10px] tracking-wider text-[#71717A] uppercase">
                        {r.category.replace(/_/g, " ")}
                      </span>
                    </div>
                    <h3 className="mt-1.5 font-medium text-white">{r.title}</h3>
                    <p className="mt-1 text-xs leading-relaxed text-[#A1A1AA]">{r.action}</p>
                  </div>

                  <Button
                    variant="outline"
                    size="sm"
                    className="shrink-0 border-[#1C1C1C] bg-[#111111] text-white hover:bg-[#1C1C1C] hover:text-white"
                    onClick={() => setChallenging(r)}
                  >
                    <ShieldQuestion className="size-4" aria-hidden />
                    Why?
                  </Button>
                </div>

                <p className="mt-2 flex items-center gap-1 text-[10px] text-[#52525B]">
                  <span className="rounded bg-[#111111] px-1 py-0.5 font-mono">
                    {r.triggered_by_rule}
                  </span>
                  <ArrowRight className="size-3" aria-hidden />
                  <span className="rounded bg-[#111111] px-1 py-0.5 font-mono">{r.policy}</span>
                </p>
              </li>
            ))}
          </ul>
        )}

        {report.requires_human_review && report.human_review_reasons.length ? (
          <div className="border-t border-l-2 border-[#1C1C1C] border-l-[#EAB308] bg-[#111111] px-4 py-3">
            <p className="mb-1 text-[10px] font-medium tracking-wider text-[#EAB308] uppercase">
              Human review required because
            </p>
            <ul className="space-y-0.5">
              {report.human_review_reasons.map((reason, i) => (
                <li key={i} className="text-[11px] leading-relaxed text-[#A1A1AA]">
                  • {reason}
                </li>
              ))}
            </ul>
          </div>
        ) : null}

        <ExpectedImpact report={report} />
      </div>

      {challenging ? <ChallengeDialog recommendation={challenging} onClose={close} /> : null}
    </>
  );
}
