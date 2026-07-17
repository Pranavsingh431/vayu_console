"use client";

import { cn } from "@/lib/utils";

/**
 * The natural experiments, and what each one tested.
 *
 * This is what makes the historical validation tangible: these are not
 * illustrations, they are the events the evidence modules were calibrated and
 * stress-tested against. The COVID row is why the traffic module exists at all;
 * had NO2 not fallen, the module would have been deleted.
 */

interface Event {
  id: string;
  label: string;
  date: string;
  year: number;
  stations: number | null;
  tested: string;
  status: "calibrated" | "verified" | "pending" | "gap";
  detail: string;
}

const EVENTS: Event[] = [
  {
    id: "odd-even-1",
    label: "Odd-Even I",
    date: "Jan 2016",
    year: 2016,
    stations: 11,
    tested: "Vehicular",
    status: "pending",
    detail: "Winter inversion dominates; two-wheelers and CNG exempt. Not yet analysed.",
  },
  {
    id: "odd-even-2",
    label: "Odd-Even II",
    date: "Apr 2016",
    year: 2016,
    stations: 11,
    tested: "Vehicular",
    status: "pending",
    detail:
      "The only unconfounded vehicle window: no stubble, no inversion. Weak treatment on 11 stations.",
  },
  {
    id: "diwali-2019",
    label: "Diwali 2019",
    date: "27 Oct 2019",
    year: 2019,
    stations: 44,
    tested: "Fire discriminant validity",
    status: "verified",
    detail:
      "VIIRS overpasses Delhi at 12:00–14:00 and 01:00–03:00 IST — zero detections in the 20:00–00:00 firework window. The biomass module cannot absorb fireworks.",
  },
  {
    id: "odd-even-3",
    label: "Odd-Even III",
    date: "Nov 2019",
    year: 2019,
    stations: 46,
    tested: "Vehicular",
    status: "pending",
    detail: "Ran during peak stubble season. The vehicular signal is buried under smoke.",
  },
  {
    id: "covid",
    label: "COVID lockdown",
    date: "Mar–Apr 2020",
    year: 2020,
    stations: 47,
    tested: "Traffic module",
    status: "calibrated",
    detail:
      "NO₂ −54.4%, SO₂ −3.7% across 901,160 rows. Power stayed essential, so SO₂ held while NO₂ halved — the differential the hypothesis required. LR 2.11 (weak). ACCEPTED.",
  },
  {
    id: "gap",
    label: "Archive gap",
    date: "2023–2024",
    year: 2023,
    stations: 1,
    tested: "—",
    status: "gap",
    detail:
      "1 station in 2023, 2 in 2024. No trend may be drawn across this. Not a data-loading bug — the archive genuinely lacks it.",
  },
];

const TONE: Record<Event["status"], string> = {
  calibrated: "border-emerald-500 bg-emerald-50 dark:bg-emerald-950/40",
  verified: "border-sky-500 bg-sky-50 dark:bg-sky-950/40",
  pending: "border-slate-300 bg-slate-50 dark:border-slate-700 dark:bg-slate-900/40",
  gap: "border-red-400 bg-red-50 dark:bg-red-950/40",
};

const BADGE: Record<Event["status"], string> = {
  calibrated: "bg-emerald-600 text-white",
  verified: "bg-sky-600 text-white",
  pending: "bg-slate-400 text-white",
  gap: "bg-red-600 text-white",
};

export function Timeline({ activeYear }: { activeYear?: number }) {
  return (
    <section className="rounded-lg border bg-card">
      <header className="border-b px-4 py-3">
        <h2 className="font-semibold">Historical validation</h2>
        <p className="mt-0.5 text-xs text-muted-foreground">
          The events each module was calibrated and stress-tested against. A module that fails its
          test is deleted, not reinterpreted.
        </p>
      </header>

      <div className="flex gap-3 overflow-x-auto p-4">
        {EVENTS.map((e) => (
          <div
            key={e.id}
            className={cn(
              "w-60 shrink-0 rounded border-l-4 p-3",
              TONE[e.status],
              activeYear === e.year && "ring-2 ring-primary",
            )}
          >
            <div className="flex items-center justify-between gap-2">
              <span className="text-sm font-medium">{e.label}</span>
              <span
                className={cn(
                  "rounded px-1.5 py-0.5 text-[9px] font-medium uppercase",
                  BADGE[e.status],
                )}
              >
                {e.status}
              </span>
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              {e.date}
              {e.stations !== null ? ` · ${e.stations} stations` : ""}
            </p>
            <p className="mt-1 text-[10px] text-muted-foreground/70 uppercase">tests: {e.tested}</p>
            <p className="mt-1.5 text-[11px] leading-snug">{e.detail}</p>
          </div>
        ))}
      </div>
    </section>
  );
}
