"use client";

import { Info, Play, Square } from "lucide-react";

import type { Presentation } from "@/lib/use-presentation";
import type { Scenario } from "@/lib/scenarios";
import { SCENARIOS, UNAVAILABLE_SCENARIOS } from "@/lib/scenarios";
import { cn } from "@/lib/utils";

/**
 * Demo Mode: one click loads a real incident.
 *
 * Each scenario re-runs the live engines against real ingested data — nothing
 * here is a fixture. `Present Incident` then walks the console through the
 * reasoning on its own.
 */
export function ScenarioBar({
  active,
  onSelect,
  presentation,
}: {
  active: Scenario;
  onSelect: (s: Scenario) => void;
  presentation: Presentation;
}) {
  return (
    <div className="flex items-center gap-6 border-b border-[#1C1C1C] bg-black px-6 py-2.5">
      <span className="text-[10px] tracking-wider text-[#71717A] uppercase">Incident</span>

      <div className="flex items-center gap-1" role="tablist" aria-label="Demo scenarios">
        {SCENARIOS.map((s) => (
          <button
            key={s.id}
            role="tab"
            aria-selected={s.id === active.id}
            onClick={() => onSelect(s)}
            disabled={presentation.active}
            className={cn(
              "rounded-md px-3 py-1.5 text-xs font-medium transition-colors duration-150",
              "disabled:cursor-not-allowed disabled:opacity-40",
              s.id === active.id
                ? "bg-white text-black"
                : "text-[#A1A1AA] hover:bg-[#111111] hover:text-white",
            )}
          >
            {s.label}
            {!s.complete ? (
              <span
                className="ml-1.5 text-[#EAB308]"
                title="Fires and weather were not ingested for this window"
              >
                ·
              </span>
            ) : null}
          </button>
        ))}

        {/* Absent on purpose, and said so. Same reason the API exposes /decision/gaps. */}
        {UNAVAILABLE_SCENARIOS.map((u) => (
          <span
            key={u.label}
            title={u.reason}
            className="flex cursor-help items-center gap-1 rounded-md px-3 py-1.5 text-xs text-[#3F3F46]"
          >
            {u.label}
            <Info className="size-3" aria-hidden />
          </span>
        ))}
      </div>

      <p className="hidden flex-1 truncate text-xs text-[#71717A] lg:block">{active.situation}</p>

      <button
        onClick={presentation.active ? presentation.stop : presentation.start}
        className={cn(
          "flex shrink-0 items-center gap-2 rounded-md px-3.5 py-1.5 text-xs font-medium",
          "transition-colors duration-150",
          presentation.active
            ? "bg-[#EF4444] text-white hover:bg-[#EF4444]/90"
            : "bg-white text-black hover:bg-white/90",
        )}
      >
        {presentation.active ? (
          <>
            <Square className="size-3 fill-current" aria-hidden />
            Stop
          </>
        ) : (
          <>
            <Play className="size-3 fill-current" aria-hidden />
            Present Incident
          </>
        )}
      </button>
    </div>
  );
}

/** A hairline progress bar during Presentation Mode. No countdown, no chrome. */
export function PresentationProgress({ presentation }: { presentation: Presentation }) {
  if (!presentation.active) return null;
  return (
    <div
      className="h-0.5 w-full bg-[#1C1C1C]"
      role="progressbar"
      aria-label="Presentation progress"
      aria-valuenow={Math.round(presentation.progress * 100)}
    >
      <div
        className="h-full bg-white transition-[width] duration-500 ease-linear"
        style={{ width: `${presentation.progress * 100}%` }}
      />
    </div>
  );
}
