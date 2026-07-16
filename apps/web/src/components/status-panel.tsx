"use client";

import type { ComponentStatus, HealthResponse, VersionResponse } from "@vayu/shared";
import { useQuery } from "@tanstack/react-query";
import { AlertCircle, CheckCircle2, Loader2, MinusCircle, RefreshCw } from "lucide-react";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { api, ApiUnreachableError, queryKeys } from "@/lib/api";

const STATUS_PRESENTATION: Record<
  ComponentStatus,
  { label: string; variant: "success" | "destructive" | "secondary"; Icon: typeof CheckCircle2 }
> = {
  ok: { label: "Operational", variant: "success", Icon: CheckCircle2 },
  unavailable: { label: "Unavailable", variant: "destructive", Icon: AlertCircle },
  not_configured: { label: "Not configured", variant: "secondary", Icon: MinusCircle },
};

function DependencyRow({
  name,
  status,
  detail,
  latencyMs,
}: {
  name: string;
  status: ComponentStatus;
  detail: string | null;
  latencyMs: number | null;
}) {
  const { label, variant, Icon } = STATUS_PRESENTATION[status];

  return (
    <div className="flex items-start justify-between gap-4 border-b py-3 last:border-b-0">
      <div className="min-w-0">
        <div className="flex items-center gap-2">
          <Icon className="size-4 shrink-0 text-muted-foreground" aria-hidden />
          <span className="text-sm font-medium capitalize">{name}</span>
        </div>
        {detail ? <p className="mt-1 text-xs text-muted-foreground">{detail}</p> : null}
      </div>
      <div className="flex shrink-0 items-center gap-2">
        {latencyMs !== null ? (
          <span className="font-mono text-xs text-muted-foreground">{latencyMs} ms</span>
        ) : null}
        <Badge variant={variant}>{label}</Badge>
      </div>
    </div>
  );
}

export function StatusPanel() {
  const health = useQuery<HealthResponse>({
    queryKey: queryKeys.health,
    queryFn: api.health,
    refetchInterval: 15_000,
  });

  const version = useQuery<VersionResponse>({
    queryKey: queryKeys.version,
    queryFn: api.version,
  });

  if (health.isPending) {
    return (
      <Card>
        <CardContent className="flex items-center gap-2 py-8 text-sm text-muted-foreground">
          <Loader2 className="size-4 animate-spin" aria-hidden />
          Checking API health…
        </CardContent>
      </Card>
    );
  }

  if (health.isError) {
    // A backend that is down is the single most likely thing a developer sees
    // here, so say what to do about it rather than just reporting an error.
    const unreachable = health.error instanceof ApiUnreachableError;

    return (
      <Card className="border-destructive/50">
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base text-destructive">
            <AlertCircle className="size-4" aria-hidden />
            API unreachable
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">{health.error.message}</p>
          {unreachable ? (
            <p className="text-sm text-muted-foreground">
              Start it with{" "}
              <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground">
                npm run dev:api
              </code>{" "}
              from the repository root.
            </p>
          ) : null}
          <Button variant="outline" size="sm" onClick={() => void health.refetch()}>
            <RefreshCw className="size-4" aria-hidden />
            Retry
          </Button>
        </CardContent>
      </Card>
    );
  }

  const isHealthy = health.data.status === "ok";

  return (
    <Card>
      <CardHeader>
        <div className="flex items-center justify-between gap-4">
          <CardTitle className="text-base">API</CardTitle>
          <Badge variant={isHealthy ? "success" : "warning"}>
            {isHealthy ? "All systems operational" : "Degraded"}
          </Badge>
        </div>
      </CardHeader>
      <CardContent>
        <dl className="mb-2 grid grid-cols-2 gap-x-4 gap-y-1 text-xs text-muted-foreground sm:grid-cols-3">
          <div>
            <dt className="inline">Environment: </dt>
            <dd className="inline font-mono text-foreground">{health.data.environment}</dd>
          </div>
          <div>
            <dt className="inline">Version: </dt>
            <dd className="inline font-mono text-foreground">{health.data.version}</dd>
          </div>
          <div>
            <dt className="inline">Commit: </dt>
            <dd className="inline font-mono text-foreground">
              {version.data?.commit?.slice(0, 7) ?? "local"}
            </dd>
          </div>
        </dl>

        <div className="mt-4">
          {Object.entries(health.data.checks).map(([name, check]) => (
            <DependencyRow
              key={name}
              name={name}
              status={check.status}
              detail={check.detail}
              latencyMs={check.latency_ms}
            />
          ))}
        </div>

        <div className="mt-4 flex items-center justify-between">
          <p className="text-xs text-muted-foreground">
            {health.isFetching ? "Refreshing…" : "Refreshes every 15s"}
          </p>
          <Button variant="ghost" size="sm" onClick={() => void health.refetch()}>
            <RefreshCw className="size-4" aria-hidden />
            Refresh
          </Button>
        </div>
      </CardContent>
    </Card>
  );
}
