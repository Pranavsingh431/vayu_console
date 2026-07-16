import type { Metadata } from "next";

import { StatusPanel } from "@/components/status-panel";
import { env } from "@/lib/env";

export const metadata: Metadata = {
  title: "Status",
  description: "Live health of the Vayu Console API and its dependencies.",
};

export default function StatusPage() {
  return (
    <main className="flex flex-1 flex-col px-6 py-16">
      <div className="mx-auto w-full max-w-2xl">
        <h1 className="text-3xl font-semibold tracking-tight text-foreground">System Status</h1>
        <p className="mt-2 text-sm text-muted-foreground">
          Live health of the Vayu Console API at{" "}
          <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs text-foreground">
            {env.apiBaseUrl}
          </code>
        </p>
        <div className="mt-8">
          <StatusPanel />
        </div>
      </div>
    </main>
  );
}
