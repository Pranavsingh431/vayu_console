"use client";

import type { DecisionReport, EvidenceReport } from "@vayu/shared";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, Loader2 } from "lucide-react";

import { EvidencePanel } from "@/components/evidence-panel";
import { RecommendationPanel } from "@/components/recommendation-panel";
import { SituationHeader } from "@/components/situation-header";
import { StationMap } from "@/components/station-map";
import { Timeline } from "@/components/timeline";
import { Button } from "@/components/ui/button";
import { api, ApiUnreachableError, queryKeys } from "@/lib/api";

/**
 * The operations console.
 *
 * The workflow is the design: Situation → Evidence → Decision → Action. An officer
 * should be able to read down the page and arrive at something they can defend.
 *
 * The demo loads the worked Diwali 2019 example, which is served from a fixed
 * context on the API side and needs no database — so the console renders even on
 * a cold Render instance with nothing ingested.
 */

function useConsoleData() {
  const evidence = useQuery<EvidenceReport>({
    queryKey: queryKeys.evidenceExample,
    queryFn: api.evidenceExample,
  });
  const decision = useQuery<DecisionReport>({
    queryKey: queryKeys.decisionExample,
    queryFn: api.decisionExample,
  });
  return { evidence, decision };
}

export function ConsoleView() {
  const { evidence, decision } = useConsoleData();

  if (evidence.isPending || decision.isPending) {
    return (
      <main className="flex flex-1 items-center justify-center">
        <p className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Loading evidence…
        </p>
      </main>
    );
  }

  if (evidence.isError || decision.isError) {
    const error = evidence.error ?? decision.error;
    const unreachable = error instanceof ApiUnreachableError;
    return (
      <main className="flex flex-1 items-center justify-center px-6">
        <div className="max-w-md rounded-lg border border-destructive/50 bg-card p-6">
          <h1 className="flex items-center gap-2 font-semibold text-destructive">
            <AlertCircle className="size-4" aria-hidden />
            API unreachable
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">{error?.message}</p>
          {unreachable ? (
            <p className="mt-2 text-sm text-muted-foreground">
              Start it with{" "}
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground">
                npm run dev:api
              </code>{" "}
              from the repository root.
            </p>
          ) : null}
          <Button
            variant="outline"
            size="sm"
            className="mt-4"
            onClick={() => void evidence.refetch()}
          >
            Retry
          </Button>
        </div>
      </main>
    );
  }

  const year = new Date(evidence.data.evaluated_at).getUTCFullYear();

  return (
    <main className="flex-1 px-4 py-6 sm:px-6">
      <div className="mx-auto max-w-7xl space-y-4">
        <header className="flex flex-wrap items-baseline justify-between gap-2">
          <div>
            <h1 className="text-2xl font-semibold tracking-tight">Operations Console</h1>
            <p className="text-sm text-muted-foreground">
              Delhi · situation, evidence, decision, action
            </p>
          </div>
          <p className="font-mono text-xs text-muted-foreground">
            engine {decision.data.engine_version} · evidence {decision.data.evidence_engine_version}
          </p>
        </header>

        {/* 1. Situation — what is happening. */}
        <SituationHeader evidence={evidence.data} decision={decision.data} />

        <div className="grid gap-4 lg:grid-cols-5">
          {/* 2. Map — where. */}
          <div className="lg:col-span-3">
            <StationMap evidence={evidence.data} />
          </div>

          {/* 3. Evidence — why we think so. */}
          <div className="lg:col-span-2">
            <EvidencePanel report={evidence.data} />
          </div>
        </div>

        {/* 4. Recommendations + 5. Challenge (inside the panel). */}
        <RecommendationPanel report={decision.data} />

        {/* 6. Timeline — how we know the modules work. */}
        <Timeline activeYear={year} />

        <footer className="pb-4 text-center text-[11px] text-muted-foreground">
          Recommendations are derived deterministically from evidence — no model and no language
          model is involved. This system does not measure source contributions, and evidence
          strengths do not sum to 100%.
        </footer>
      </div>
    </main>
  );
}
