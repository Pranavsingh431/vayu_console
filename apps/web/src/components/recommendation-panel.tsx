"use client";

import type { DecisionReport, Priority, Recommendation } from "@vayu/shared";
import { AlertTriangle, ArrowRight, ShieldQuestion, X } from "lucide-react";
import { useState } from "react";

import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

/**
 * Recommendations, and the Challenge affordance.
 *
 * The Challenge dialog is the point of the product. It shows the officer exactly
 * what the advice rests on, what argues against it, and which assumptions must
 * hold — everything they need to defend it in a meeting, or abandon it.
 */

const PRIORITY_TONE: Record<Priority, string> = {
  immediate: "bg-red-600 text-white",
  high: "bg-orange-500 text-white",
  routine: "bg-slate-500 text-white",
  informational: "bg-slate-300 text-slate-800 dark:bg-slate-700 dark:text-slate-200",
};

function ChallengeDialog({
  recommendation,
  onClose,
}: {
  recommendation: Recommendation;
  onClose: () => void;
}) {
  const r = recommendation;
  return (
    <div
      className="fixed inset-0 z-50 flex items-start justify-center overflow-y-auto bg-black/50 p-4 sm:p-8"
      onClick={onClose}
      role="dialog"
      aria-modal="true"
      aria-label={`Why: ${r.title}`}
    >
      <div
        className="w-full max-w-3xl rounded-lg border bg-card shadow-xl"
        onClick={(e) => e.stopPropagation()}
      >
        <header className="flex items-start justify-between gap-4 border-b px-5 py-4">
          <div>
            <p className="text-xs text-muted-foreground uppercase">Why this recommendation?</p>
            <h3 className="mt-0.5 text-lg font-semibold">{r.title}</h3>
          </div>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-muted-foreground hover:text-foreground"
          >
            <X className="size-5" />
          </button>
        </header>

        <div className="space-y-5 px-5 py-4 text-sm">
          {/* The trace is the spine of the whole feature: advice back to observation. */}
          <div>
            <p className="mb-2 text-xs font-medium text-muted-foreground uppercase">
              Decision trace
            </p>
            <ol className="space-y-2">
              {r.decision_trace.map((t, i) => (
                <li key={i} className="flex gap-3">
                  <span className="w-24 shrink-0 pt-0.5 text-[10px] font-medium text-muted-foreground/60 uppercase">
                    {t.step}
                  </span>
                  <div className="min-w-0 flex-1">
                    <span className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs">
                      {t.identifier}
                    </span>
                    <p className="mt-1 text-xs text-muted-foreground">{t.detail}</p>
                  </div>
                </li>
              ))}
            </ol>
          </div>

          <div className="grid gap-4 sm:grid-cols-2">
            <div>
              <p className="mb-1.5 text-xs font-medium text-emerald-700 uppercase dark:text-emerald-400">
                Supporting evidence
              </p>
              {r.supporting_evidence.length ? (
                <ul className="space-y-1">
                  {r.supporting_evidence.map((o, i) => (
                    <li key={i} className="text-xs text-muted-foreground">
                      + {o.label}
                      {o.value !== null ? (
                        <span className="font-mono text-foreground"> {o.value}</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground">None recorded.</p>
              )}
            </div>

            {/* Never hidden. The officer needs the counter-argument before
                someone else in the meeting supplies it. */}
            <div>
              <p className="mb-1.5 text-xs font-medium text-red-700 uppercase dark:text-red-400">
                Contradicting evidence
              </p>
              {r.contradicting_evidence.length ? (
                <ul className="space-y-1">
                  {r.contradicting_evidence.map((o, i) => (
                    <li key={i} className="text-xs text-muted-foreground">
                      − {o.label}
                      {o.value !== null ? (
                        <span className="font-mono text-foreground"> {o.value}</span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-xs text-muted-foreground">None recorded.</p>
              )}
            </div>
          </div>

          <div className="rounded border bg-muted/50 p-3">
            <p className="mb-1 text-xs font-medium text-muted-foreground uppercase">
              How far this can be pushed
            </p>
            <p className="text-xs">{r.confidence_note}</p>
          </div>

          {r.assumptions.length ? (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted-foreground uppercase">
                Assumptions
              </p>
              <ul className="space-y-1">
                {r.assumptions.map((a, i) => (
                  <li key={i} className="text-xs text-muted-foreground">
                    • {a}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          {r.limitations.length ? (
            <div>
              <p className="mb-1.5 text-xs font-medium text-muted-foreground uppercase">
                Limitations
              </p>
              <ul className="space-y-1">
                {r.limitations.map((l, i) => (
                  <li key={i} className="text-xs text-muted-foreground">
                    • {l}
                  </li>
                ))}
              </ul>
            </div>
          ) : null}

          <div className="rounded border border-amber-300 bg-amber-50 p-3 dark:border-amber-900 dark:bg-amber-950/40">
            <p className="text-xs">
              <span className="font-medium">To challenge this:</span> check the contradicting
              evidence and the assumptions first. If an assumption does not hold at this station,
              the recommendation does not follow.
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
    <div className="border-t px-4 py-3">
      <p className="mb-1 text-xs font-medium text-muted-foreground uppercase">Expected impact</p>
      {fireDriven ? (
        <p className="text-xs">
          If upwind fire activity declines, air quality is expected to improve.{" "}
          <span className="font-medium">Reassess within 6 hours.</span>
          <span className="text-muted-foreground">
            {" "}
            Reason: the recommendation rests on transient fire evidence — satellite detections from
            the last 24 hours, which will have moved on.
          </span>
        </p>
      ) : (
        <p className="text-xs">
          <span className="font-medium">Reassess at the next commute peak.</span>
          <span className="text-muted-foreground">
            {" "}
            Reason: the recommendation rests on traffic evidence, which follows a daily cycle rather
            than a weather event.
          </span>
        </p>
      )}
      <p className="mt-1.5 text-[11px] text-muted-foreground">
        Qualitative guidance only. The system does not forecast concentrations and cannot estimate
        the effect of any action.
      </p>
    </div>
  );
}

export function RecommendationPanel({ report }: { report: DecisionReport }) {
  const [challenging, setChallenging] = useState<Recommendation | null>(null);

  return (
    <section className="rounded-lg border bg-card">
      <header className="flex items-center justify-between border-b px-4 py-3">
        <h2 className="font-semibold">Recommendations</h2>
        {report.requires_human_review ? (
          <span className="flex items-center gap-1 rounded bg-amber-100 px-2 py-0.5 text-[10px] font-medium text-amber-800 uppercase dark:bg-amber-950 dark:text-amber-300">
            <AlertTriangle className="size-3" aria-hidden />
            human review
          </span>
        ) : null}
      </header>

      {report.conflict_note ? (
        <div className="border-b bg-amber-50 px-4 py-2.5 dark:bg-amber-950/40">
          <p className="text-xs">{report.conflict_note}</p>
        </div>
      ) : null}

      {report.recommendations.length === 0 ? (
        <div className="px-4 py-6">
          <p className="text-sm font-medium">
            {report.overall_status === "insufficient_evidence"
              ? "No recommendation can be justified."
              : "No action recommended."}
          </p>
          <p className="mt-1 text-xs text-muted-foreground">{report.summary}</p>
        </div>
      ) : (
        <ul>
          {report.recommendations.map((r) => (
            <li key={r.id} className="border-b px-4 py-3 last:border-b-0">
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
                    <span className="text-[10px] text-muted-foreground uppercase">
                      {r.category.replace(/_/g, " ")}
                    </span>
                  </div>
                  <h3 className="mt-1.5 font-medium">{r.title}</h3>
                  <p className="mt-1 text-xs text-muted-foreground">{r.action}</p>
                </div>

                <Button
                  variant="outline"
                  size="sm"
                  className="shrink-0"
                  onClick={() => setChallenging(r)}
                >
                  <ShieldQuestion className="size-4" aria-hidden />
                  Why?
                </Button>
              </div>

              <p className="mt-2 flex items-center gap-1 text-[11px] text-muted-foreground/80">
                <span className="rounded bg-muted px-1 py-0.5 font-mono">
                  {r.triggered_by_rule}
                </span>
                <ArrowRight className="size-3" aria-hidden />
                <span className="rounded bg-muted px-1 py-0.5 font-mono">{r.policy}</span>
              </p>
            </li>
          ))}
        </ul>
      )}

      {report.requires_human_review && report.human_review_reasons.length ? (
        <div className="border-t bg-amber-50/50 px-4 py-3 dark:bg-amber-950/20">
          <p className="mb-1 text-xs font-medium">Human review required because:</p>
          <ul className="space-y-0.5">
            {report.human_review_reasons.map((reason, i) => (
              <li key={i} className="text-[11px] text-muted-foreground">
                • {reason}
              </li>
            ))}
          </ul>
        </div>
      ) : null}

      <ExpectedImpact report={report} />

      {challenging ? (
        <ChallengeDialog recommendation={challenging} onClose={() => setChallenging(null)} />
      ) : null}
    </section>
  );
}
