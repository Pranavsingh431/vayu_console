"use client";

import type { EvidenceReport } from "@vayu/shared";

import type { Scenario } from "@/lib/scenarios";
import { cn } from "@/lib/utils";

/**
 * The spatial picture: the station, the wind, and where the fires are.
 *
 * Deliberately not a tiled basemap. A street map would be decoration — the thing
 * that carries the reasoning is the geometry: wind arriving from 315°, fires
 * sitting upwind 200 km away in Punjab. That is the argument the biomass module
 * makes, drawn.
 *
 * Rendered as SVG so it has no tile server, no API key, and no SSR workaround —
 * it cannot fail in a demo.
 */

// Rough Delhi ⇄ Punjab stubble belt frame (lon/lat), so both fit in one view.
const WEST = 73.5;
const EAST = 78.5;
const SOUTH = 27.5;
const NORTH = 31.5;

const W = 560;
const H = 420;

function project(lon: number, lat: number): [number, number] {
  const x = ((lon - WEST) / (EAST - WEST)) * W;
  // SVG y grows downward; latitude grows upward.
  const y = H - ((lat - SOUTH) / (NORTH - SOUTH)) * H;
  return [x, y];
}

function find(report: EvidenceReport, label: string): number | null {
  for (const e of report.evidence) {
    for (const o of [...e.supporting_observations, ...e.contradicting_observations]) {
      if (o.label === label && typeof o.value === "number") return o.value;
    }
  }
  return null;
}

function fireCount(report: EvidenceReport): number | null {
  for (const e of report.evidence) {
    for (const o of e.supporting_observations) {
      const m = /^(\d+) fire detections upwind/.exec(o.label);
      if (m) return Number(m[1]);
    }
  }
  return null;
}

const DELHI: [number, number] = [77.209, 28.6139];

// Representative transport distance, in degrees, for drawing the upwind fire
// aggregate. ~1.9° ≈ 200 km, the Punjab-to-Delhi distance the biomass module's
// kernel is built around.
const UPWIND_DEGREES = 1.9;

export function StationMap({
  evidence,
  scenario,
  showFires = true,
}: {
  evidence: EvidenceReport;
  scenario?: Scenario;
  showFires?: boolean;
}) {
  const windFrom = find(evidence, "Wind direction (from)");
  const fires = fireCount(evidence);
  const biomass = evidence.evidence.find((e) => e.hypothesis === "biomass");

  const [dx, dy] = project(...DELHI);

  // Meteorological convention: wind_direction is the bearing the wind blows FROM.
  // The arrow must therefore point from that bearing toward the station.
  const windRad = windFrom !== null ? ((windFrom + 180) * Math.PI) / 180 : null;
  const arrowLen = 90;
  const windTail =
    windRad !== null
      ? [dx - Math.sin(windRad) * arrowLen, dy + Math.cos(windRad) * arrowLen]
      : null;

  // Fires are shown in the upwind sector at a representative transport distance,
  // not at their true coordinates: the module reasons over an aggregate influence,
  // and plotting 1,593 individual pixels would imply a precision it does not use.
  // The fire sits AT the upwind bearing — i.e. at `windFrom` itself, since that
  // is the direction the wind arrives from. Offsetting by 180 would place it
  // downwind, where its smoke could never reach the station.
  const fireCentre =
    windFrom !== null
      ? project(
          DELHI[0] + Math.sin((windFrom * Math.PI) / 180) * UPWIND_DEGREES,
          DELHI[1] + Math.cos((windFrom * Math.PI) / 180) * UPWIND_DEGREES,
        )
      : null;

  return (
    <>
      <header className="flex shrink-0 items-center justify-between border-b border-[#1C1C1C] px-4 py-3">
        <h2 className="text-sm font-medium text-white">Transport geometry</h2>
        <span className="text-[10px] text-[#71717A]">Delhi &amp; upwind stubble belt</span>
      </header>

      <svg
        viewBox={`0 0 ${W} ${H}`}
        className="h-auto w-full"
        role="img"
        aria-label="Station, wind and upwind fires"
      >
        <rect width={W} height={H} className="fill-black" />

        {/* Graticule — orientation, not decoration. */}
        {[74, 75, 76, 77, 78].map((lon) => {
          const [x] = project(lon, SOUTH);
          return (
            <g key={lon}>
              <line
                x1={x}
                y1={0}
                x2={x}
                y2={H}
                className="stroke-slate-200 dark:stroke-slate-800"
                strokeWidth={1}
              />
              <text x={x + 3} y={H - 5} className="fill-[#3F3F46] text-[9px]">
                {lon}°E
              </text>
            </g>
          );
        })}
        {[28, 29, 30, 31].map((lat) => {
          const [, y] = project(WEST, lat);
          return (
            <g key={lat}>
              <line
                x1={0}
                y1={y}
                x2={W}
                y2={y}
                className="stroke-slate-200 dark:stroke-slate-800"
                strokeWidth={1}
              />
              <text x={4} y={y - 4} className="fill-[#3F3F46] text-[9px]">
                {lat}°N
              </text>
            </g>
          );
        })}

        {/* Punjab / Haryana stubble belt. */}
        <text
          x={project(75.2, 30.9)[0]}
          y={project(75.2, 30.9)[1]}
          className="fill-[#52525B] text-[10px] font-medium tracking-wider"
        >
          PUNJAB
        </text>
        <text
          x={project(76.2, 29.4)[0]}
          y={project(76.2, 29.4)[1]}
          className="fill-[#52525B] text-[10px] font-medium tracking-wider"
        >
          HARYANA
        </text>

        {/* Upwind fire cluster. Size encodes count, not extent. */}
        {fireCentre && fires ? (
          <g
            className={cn(
              "transition-opacity duration-300",
              showFires ? "opacity-100" : "opacity-0",
            )}
          >
            <circle
              cx={fireCentre[0]}
              cy={fireCentre[1]}
              r={Math.min(70, 18 + Math.log10(Math.max(fires, 1)) * 16)}
              className="fill-[#EF4444]/15 stroke-[#EF4444]"
              strokeWidth={1.5}
              strokeDasharray="4 3"
            />
            <text
              x={fireCentre[0]}
              y={fireCentre[1] - 4}
              textAnchor="middle"
              className="fill-[#EF4444] text-[11px] font-semibold"
            >
              {fires.toLocaleString()} fires
            </text>
            <text
              x={fireCentre[0]}
              y={fireCentre[1] + 9}
              textAnchor="middle"
              className="fill-[#EF4444]/70 text-[9px]"
            >
              upwind, last 24h
            </text>
          </g>
        ) : null}

        {/* Wind arrow: from the upwind bearing toward the station. */}
        {windTail ? (
          <g>
            <defs>
              <marker
                id="wind-head"
                markerWidth="8"
                markerHeight="8"
                refX="6"
                refY="3"
                orient="auto"
              >
                <path d="M0,0 L0,6 L7,3 z" className="fill-[#A1A1AA]" />
              </marker>
            </defs>
            <line
              x1={windTail[0]}
              y1={windTail[1]}
              x2={dx - 14}
              y2={dy - 14}
              className="stroke-[#A1A1AA]"
              strokeWidth={2.5}
              markerEnd="url(#wind-head)"
            />
            <text
              x={(windTail[0] + dx) / 2}
              y={(windTail[1] + dy) / 2 - 8}
              className="fill-[#A1A1AA] text-[10px] font-medium"
            >
              wind {windFrom?.toFixed(0)}°
            </text>
          </g>
        ) : null}

        {/* The station. */}
        <g>
          <circle
            cx={dx}
            cy={dy}
            r={9}
            className={
              biomass?.strength === "strong" || biomass?.strength === "very_strong"
                ? "fill-[#EF4444] stroke-white"
                : "fill-white stroke-black"
            }
            strokeWidth={2}
          />
          <text x={dx + 14} y={dy + 4} className="fill-white text-[11px] font-semibold">
            {evidence.station.split(",")[0]}
          </text>
        </g>
      </svg>

      <footer className="shrink-0 border-t border-[#1C1C1C] px-4 py-2 text-[10px] leading-relaxed text-[#71717A]">
        {scenario && !scenario.complete
          ? "Fire and weather observations were not collected for this window."
          : "Fires shown as an aggregate in the upwind sector at representative transport distance, not at true coordinates."}
      </footer>
    </>
  );
}
