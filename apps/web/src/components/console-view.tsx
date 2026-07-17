"use client";

import type { DecisionReport, EvidenceReport } from "@vayu/shared";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle } from "lucide-react";
import { useCallback, useEffect, useState } from "react";

import { EvidencePanel } from "@/components/evidence-panel";
import { RecommendationPanel } from "@/components/recommendation-panel";
import { PresentationProgress, ScenarioBar } from "@/components/scenario-bar";
import { SituationHeader } from "@/components/situation-header";
import { StationMap } from "@/components/station-map";
import { Timeline } from "@/components/timeline";
import { api, ApiUnreachableError, queryKeys } from "@/lib/api";
import { DIWALI_EXAMPLE, type Scenario } from "@/lib/scenarios";
import { usePresentation } from "@/lib/use-presentation";
import { cn } from "@/lib/utils";

/**
 * The operations console.
 *
 * The layout IS the workflow: Situation across the top, then Map → Evidence →
 * Decision left to right, then the historical record beneath. An officer reads it
 * in the order the reasoning happens.
 *
 * The page never scrolls; panels do. On a control-room screen, scrolling the page
 * means losing the number you were looking at.
 */

function Panel({
  children,
  className,
  reveal = true,
}: {
  children: React.ReactNode;
  className?: string;
  reveal?: boolean;
}) {
  return (
    <section
      className={cn(
        "flex min-h-0 flex-col overflow-hidden rounded-md border border-[#1C1C1C] bg-[#0A0A0A]",
        "transition-opacity duration-200 ease-out",
        reveal ? "opacity-100" : "pointer-events-none opacity-0",
        className,
      )}
    >
      {children}
    </section>
  );
}

function Skeleton() {
  return (
    <div className="flex h-dvh flex-col bg-black">
      <div className="h-[68px] animate-pulse border-b border-[#1C1C1C] bg-[#0A0A0A]" />
      <div className="h-[45px] animate-pulse border-b border-[#1C1C1C] bg-black" />
      <div className="grid flex-1 grid-cols-12 gap-3 p-3">
        <div className="col-span-5 animate-pulse rounded-md border border-[#1C1C1C] bg-[#0A0A0A]" />
        <div className="col-span-3 animate-pulse rounded-md border border-[#1C1C1C] bg-[#0A0A0A]" />
        <div className="col-span-4 animate-pulse rounded-md border border-[#1C1C1C] bg-[#0A0A0A]" />
      </div>
      <div className="mx-3 mb-3 h-32 animate-pulse rounded-md border border-[#1C1C1C] bg-[#0A0A0A]" />
      <span className="sr-only">Loading incident</span>
    </div>
  );
}

function Unreachable({ error, onRetry }: { error: Error | null; onRetry: () => void }) {
  const unreachable = error instanceof ApiUnreachableError;
  return (
    <div className="flex h-dvh items-center justify-center bg-black px-6">
      <div className="max-w-md rounded-md border border-[#1C1C1C] bg-[#0A0A0A] p-6">
        <h1 className="flex items-center gap-2 font-medium text-white">
          <AlertCircle className="size-4 text-[#EF4444]" aria-hidden />
          Cannot reach the analysis service
        </h1>
        <p className="mt-2 text-sm text-[#A1A1AA]">
          {unreachable
            ? "The console is running, but the browser could not complete a request to the analysis service."
            : "The service responded, but not with a usable report."}
        </p>
        {unreachable ? (
          <div className="mt-3 space-y-1.5 text-xs text-[#71717A]">
            <p>Two causes look identical from here, and the browser will not say which:</p>
            <p>
              <span className="text-[#A1A1AA]">The service is down or asleep.</span> On the free
              tier the first request after idle can take up to a minute.
            </p>
            <p>
              <span className="text-[#A1A1AA]">
                The service is healthy but refusing this origin.
              </span>{" "}
              Its <code className="text-white">CORS_ORIGINS</code> must list this site&apos;s URL.
            </p>
          </div>
        ) : null}
        <button
          onClick={onRetry}
          className="mt-4 rounded-md border border-[#1C1C1C] bg-[#111111] px-3 py-1.5 text-xs font-medium text-white transition-colors duration-150 hover:bg-[#1C1C1C]"
        >
          Try again
        </button>
      </div>
    </div>
  );
}

export function ConsoleView() {
  const [scenario, setScenario] = useState<Scenario>(DIWALI_EXAMPLE);
  const presentation = usePresentation();
  const [autoChallenge, setAutoChallenge] = useState(false);

  const isExample = scenario.id === DIWALI_EXAMPLE.id;

  // The Diwali example is served from a fixed context and needs no database, so
  // the demo survives a cold Render instance. Other scenarios hit the live
  // engines against real ingested data.
  //
  // Each query is self-contained rather than reading the other's state: a query
  // that depends on another's `.data` fires against stale values the moment the
  // scenario changes, which in a live demo shows the wrong incident's evidence.
  const evidence = useQuery<EvidenceReport>({
    queryKey: queryKeys.scenarioEvidence(scenario.id, scenario.at, isExample),
    queryFn: () => (isExample ? api.evidenceExample() : api.evidenceForScenario(scenario.at)),
  });

  const decision = useQuery<DecisionReport>({
    queryKey: queryKeys.scenarioDecision(scenario.id, scenario.at, isExample),
    queryFn: async () => {
      if (isExample) return api.decisionExample();
      // Re-fetch rather than borrow: the evidence query is cached, so this is a
      // cache hit in practice and correct regardless.
      const report = await api.evidenceForScenario(scenario.at);
      return api.decision(report);
    },
  });

  const onSelect = useCallback((s: Scenario) => {
    setScenario(s);
    setAutoChallenge(false);
  }, []);

  // Presentation Mode opens the Challenge modal on its own — the step that shows
  // judges the reasoning instead of describing it.
  useEffect(() => {
    setAutoChallenge(presentation.active && presentation.step === "challenge");
  }, [presentation.active, presentation.step]);

  if (evidence.isPending || decision.isPending) return <Skeleton />;

  if (evidence.isError || decision.isError) {
    return (
      <Unreachable
        error={evidence.error ?? decision.error}
        onRetry={() => void evidence.refetch()}
      />
    );
  }

  return (
    <div className="flex h-dvh flex-col overflow-hidden bg-black">
      <SituationHeader evidence={evidence.data} decision={decision.data} />
      <ScenarioBar active={scenario} onSelect={onSelect} presentation={presentation} />
      <PresentationProgress presentation={presentation} />

      {/* Map | Evidence | Recommendations — the reasoning, left to right. */}
      <div className="grid min-h-0 flex-1 grid-cols-12 gap-3 p-3">
        <Panel className="col-span-5" reveal={presentation.reached("wind")}>
          <StationMap
            evidence={evidence.data}
            scenario={scenario}
            showFires={presentation.reached("fires")}
          />
        </Panel>

        <Panel className="col-span-3" reveal={presentation.reached("evidence")}>
          <EvidencePanel report={evidence.data} scenario={scenario} />
        </Panel>

        <Panel className="col-span-4" reveal={presentation.reached("recommendations")}>
          <RecommendationPanel
            report={decision.data}
            autoOpenChallenge={autoChallenge}
            onChallengeClose={() => setAutoChallenge(false)}
          />
        </Panel>
      </div>

      <div className="px-3 pb-3">
        <Panel reveal={presentation.reached("timeline")}>
          <Timeline activeYear={scenario.year} highlight={presentation.step === "timeline"} />
        </Panel>
      </div>
    </div>
  );
}
