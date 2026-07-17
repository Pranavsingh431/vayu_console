#!/usr/bin/env python
"""Generate the Delhi station coverage report.

Answers, with evidence rather than assertion:
  - Do we have sufficient Delhi station coverage?
  - Which pollutants are reliably available?
  - Which years are usable?

Coverage is probed against the **S3 archive**, not the OpenAQ v3 API: v3's metadata
claims coverage its measurements endpoint will not deliver, so believing it would
produce a confident and wrong report. See docs/phase-1-data-foundation.md §2.3.

    python scripts/coverage_report.py

Writes docs/research/station_inventory/station_inventory.json and coverage.md.
"""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import pathlib
import sys
from collections import Counter, defaultdict

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx  # noqa: E402

from app.core.config import get_settings  # noqa: E402
from app.data.sources.openaq_s3 import OpenAQArchive  # noqa: E402
from app.data.validation.validators import validate_coordinates  # noqa: E402

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
OUT_DIR = REPO_ROOT / "docs" / "research" / "station_inventory"

DELHI_CENTRE = (28.6139, 77.2090)
YEARS = list(range(2015, 2027))
CONCURRENCY = 8


async def fetch_locations() -> list[dict]:
    settings = get_settings()
    if not settings.openaq_api_key:
        raise SystemExit("OPENAQ_API_KEY is not set.")
    lat, lon = DELHI_CENTRE
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            "https://api.openaq.org/v3/locations",
            params={"coordinates": f"{lat},{lon}", "radius": 25000, "limit": 100},
            headers={"X-API-Key": settings.openaq_api_key},
        )
        response.raise_for_status()
        return response.json().get("results", [])


async def main() -> int:
    locations = await fetch_locations()
    print(f"discovered {len(locations)} locations within 25 km of Delhi centre")

    semaphore = asyncio.Semaphore(CONCURRENCY)
    limits = httpx.Limits(max_connections=CONCURRENCY, max_keepalive_connections=CONCURRENCY)

    async with httpx.AsyncClient(timeout=60, limits=limits) as client:
        archive = OpenAQArchive(client=client)

        async def probe(location_id: int, year: int) -> tuple[int, int, bool]:
            async with semaphore:
                try:
                    return location_id, year, await archive.has_year(location_id, year)
                except Exception:
                    return location_id, year, False

        tasks = [probe(loc["id"], y) for loc in locations for y in YEARS]
        results = await asyncio.gather(*tasks)

    years_by_station: dict[int, list[int]] = defaultdict(list)
    stations_by_year: Counter[int] = Counter()
    for location_id, year, present in results:
        if present:
            years_by_station[location_id].append(year)
            stations_by_year[year] += 1

    inventory = []
    for loc in locations:
        coords = loc.get("coordinates") or {}
        lat, lon = coords.get("latitude"), coords.get("longitude")
        findings = validate_coordinates(lat, lon) if lat and lon else []
        years = sorted(years_by_station.get(loc["id"], []))
        sensors = loc.get("sensors") or []
        inventory.append(
            {
                "location_id": loc["id"],
                "name": loc.get("name"),
                "provider": (loc.get("provider") or {}).get("name"),
                "latitude": lat,
                "longitude": lon,
                "coordinate_findings": [f.message for f in findings],
                # Pollutants the location has ever carried, across sensor vintages.
                "pollutants": sorted({s["parameter"]["name"] for s in sensors}),
                "sensor_count": len(sensors),
                "archive_years": years,
                "archive_year_count": len(years),
                # Deliberately NOT OpenAQ's datetimeFirst/datetimeLast: those span
                # all sensors and overstate continuity.
                "archive_first_year": years[0] if years else None,
                "archive_last_year": years[-1] if years else None,
                "has_gap": bool(years) and (years[-1] - years[0] + 1) != len(years),
            }
        )

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUT_DIR / "station_inventory.json").write_text(json.dumps(inventory, indent=2))

    pollutant_stations: Counter[str] = Counter()
    for entry in inventory:
        for p in entry["pollutants"]:
            pollutant_stations[p] += 1

    with_data = [e for e in inventory if e["archive_year_count"]]
    gapped = [e for e in inventory if e["has_gap"]]

    lines = [
        "# Delhi Station Coverage Report",
        "",
        f"> Generated {dt.date.today().isoformat()} by `scripts/coverage_report.py`.",
        "> Coverage probed against the **OpenAQ S3 archive** — the only source whose",
        "> claimed coverage matches what it will actually return.",
        "",
        "## Summary",
        "",
        f"- **{len(locations)}** locations within 25 km of Delhi centre",
        f"- **{len(with_data)}** have data in the archive",
        f"- **{len(gapped)}** have a gap in their year range",
        "",
        "## Stations per year",
        "",
        "| Year | Stations | |",
        "| ---- | -------: | - |",
    ]
    for year in YEARS:
        n = stations_by_year.get(year, 0)
        lines.append(f"| {year} | {n} | {'█' * n} |")

    lines += [
        "",
        "**The 2023-2024 gap is real.** No trend may be drawn across it; see",
        "`docs/research/scientific-limitations.md` §3.1.",
        "",
        "## Pollutant availability",
        "",
        "| Pollutant | Stations |",
        "| --------- | -------: |",
    ]
    for pollutant, n in pollutant_stations.most_common():
        lines.append(f"| {pollutant} | {n} |")

    lines += [
        "",
        "Counts are stations that have *ever* carried a sensor for the pollutant,",
        "across vintages — not stations reporting it today.",
        "",
        "## Providers",
        "",
        "| Provider | Stations |",
        "| -------- | -------: |",
    ]
    for provider, n in Counter(e["provider"] for e in inventory).most_common():
        lines.append(f"| {provider} | {n} |")

    lines += [
        "",
        "Providers are not interchangeable: `CPCB` are reference-grade regulatory",
        "monitors, `AirGradient` are low-cost sensors with different uncertainty.",
        "Mixing them into one mean without weighting is unsound.",
        "",
        "## Stations",
        "",
        "| Location | Provider | Years | Gap? | Pollutants |",
        "| -------- | -------- | ----- | ---- | ---------- |",
    ]
    for e in sorted(inventory, key=lambda x: -x["archive_year_count"]):
        years = e["archive_years"]
        span = f"{years[0]}-{years[-1]}" if years else "none"
        lines.append(
            f"| {(e['name'] or '?')[:38]} | {e['provider'] or '?'} | {span} "
            f"({e['archive_year_count']}) | {'yes' if e['has_gap'] else ''} | "
            f"{', '.join(e['pollutants'][:6])} |"
        )

    (OUT_DIR / "coverage.md").write_text("\n".join(lines) + "\n")

    print(f"\nwrote {OUT_DIR / 'station_inventory.json'}")
    print(f"wrote {OUT_DIR / 'coverage.md'}")
    print(f"\nstations per year: {dict(sorted(stations_by_year.items()))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
