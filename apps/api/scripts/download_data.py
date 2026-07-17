#!/usr/bin/env python
"""Download → validate → store → query, for one event.

Deliberately a script and not a scheduler. Automation before correctness only makes
wrong data arrive on time; once this is right by hand, it is worth automating.

Usage, narrowest first:

    # one station, one pollutant, one day  (the vertical slice)
    python scripts/download_data.py diwali-2019 --station 5541 --parameter pm25 --days 1

    # the full event: every Delhi station, the whole window, fires and weather
    python scripts/download_data.py diwali-2019

    # what is actually in the database
    python scripts/download_data.py query

Run from apps/api with the virtualenv active.
"""

from __future__ import annotations

import argparse
import asyncio
import datetime as dt
import json
import logging
import pathlib
import sys
from dataclasses import asdict

# Allow `python scripts/download_data.py` from apps/api without installing.
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import httpx
from sqlalchemy import func, select

from app.core.config import get_settings
from app.core.logging import configure_logging
from app.data.ingest.store import (
    refresh_station_extents,
    store_archive_records,
    store_fire_records,
    store_weather_records,
)
from app.data.sources.firms import FirmsClient
from app.data.sources.open_meteo import OpenMeteoArchive
from app.data.sources.openaq_s3 import IST, OpenAQArchive
from app.data.validation.validators import Severity, validate_series
from app.database.session import dispose_engine, get_session_factory
from app.models import FireDetection, Measurement, Station, WeatherObservation

logger = logging.getLogger("vayu.download")

REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
RAW_DIR = REPO_ROOT / "data" / "raw"

# ---------------------------------------------------------------------------
# Event definition
# ---------------------------------------------------------------------------

# Diwali 2019 fell on 27 October 2019 — inside peak stubble-burning season, which
# is precisely why it is the gate: fireworks and Punjab smoke arrive together, and
# separating them is the product's core claim.
DIWALI_2019 = dt.date(2019, 10, 27)
# A baseline before and a decay after; a single day cannot show an anomaly.
EVENT_START = dt.date(2019, 10, 20)
EVENT_END = dt.date(2019, 11, 3)

DELHI_CENTRE = (28.6139, 77.2090)
# Wide enough to include the Punjab/Haryana stubble belt upwind of Delhi:
# west, south, east, north.
STUBBLE_BBOX = (74.0, 28.0, 78.0, 31.0)

# Burari Crossing — verified to hold 300 rows across 5 pollutants on 2019-10-27.
DEFAULT_STATION = 5541

# Calibration windows for the Evidence Engine (docs/research/inference.md §5.5).
# A natural experiment is a period where the hypothesis is known by external fact,
# which is the only place P(evidence | hypothesis) becomes observable.
EVENTS: dict[str, tuple[dt.date, dt.date, str]] = {
    # Diwali 2019 — the Phase 1 gate. Confounded with peak stubble burning.
    "diwali-2019": (dt.date(2019, 10, 20), dt.date(2019, 11, 3), "fireworks + stubble"),
    # COVID lockdown — traffic ~0 by order, but construction and industry stopped
    # too. Power generation stayed essential, which is what makes the NO2/SO2
    # ratio a discriminating test rather than a confounded one.
    "covid-2020": (dt.date(2020, 3, 1), dt.date(2020, 4, 30), "traffic ~0 (confounded)"),
    # Odd-Even II — the only unconfounded vehicle window we have: no stubble, no
    # winter inversion. Weak treatment (2-wheelers and CNG exempt), 11 stations.
    "odd-even-2016": (dt.date(2016, 4, 1), dt.date(2016, 5, 15), "partial traffic cut"),
}

# Parallel S3 reads. The archive is a CDN with no documented rate limit, so the
# binding constraint is local: at 16 concurrent connections macOS ran out of
# ephemeral ports mid-run ("Can't assign requested address"). 8 is still ~6x
# faster than sequential and leaves ports for the database pool.
CONCURRENCY = 8


def _stamp(day: dt.date) -> str:
    return day.strftime("%Y%m%d")


def _write_raw(name: str, payload: object) -> pathlib.Path:
    """Persist exactly what a source returned. raw/ is immutable and never edited."""
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    path = RAW_DIR / name
    path.write_text(json.dumps(payload, indent=2, default=str))
    return path


# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------


async def discover_delhi_stations(radius_m: int = 25000) -> list[int]:
    """Location ids near Delhi, from the OpenAQ v3 metadata API.

    v3 is used for discovery only. Its measurements endpoint is not trustworthy —
    see docs/phase-1-data-foundation.md §2.3.
    """
    import httpx

    settings = get_settings()
    if not settings.openaq_api_key:
        raise SystemExit("OPENAQ_API_KEY is not set; needed for station discovery.")

    lat, lon = DELHI_CENTRE
    async with httpx.AsyncClient(timeout=60) as client:
        response = await client.get(
            "https://api.openaq.org/v3/locations",
            params={"coordinates": f"{lat},{lon}", "radius": radius_m, "limit": 100},
            headers={"X-API-Key": settings.openaq_api_key},
        )
        response.raise_for_status()
        results = response.json().get("results", [])

    _write_raw("openaq_delhi_locations.json", results)
    return [r["id"] for r in results]


async def ingest_measurements(
    station_ids: list[int], start: dt.date, end: dt.date, parameter: str | None
) -> dict[str, int]:
    """Download and store archive readings for the window.

    Days are fetched concurrently over one shared connection pool. Sequentially,
    96 stations x 15 days is 1,440 round trips to S3 and takes over half an hour;
    the archive is a CDN and has no objection to parallel reads. Writes stay
    per-station and sequential — the bottleneck is the network, not the database.
    """
    factory = get_session_factory()
    totals = {"records": 0, "stored": 0, "stations_with_data": 0}
    days = [start + dt.timedelta(days=n) for n in range((end - start).days + 1)]

    limits = httpx.Limits(max_connections=CONCURRENCY, max_keepalive_connections=CONCURRENCY)
    async with httpx.AsyncClient(timeout=60, limits=limits) as client:
        archive = OpenAQArchive(client=client)
        semaphore = asyncio.Semaphore(CONCURRENCY)

        async def fetch(station_id: int, day: dt.date) -> list:
            async with semaphore:
                try:
                    return await archive.fetch_day(station_id, day)
                except Exception as exc:
                    logger.warning(
                        "archive fetch failed",
                        extra={"station": station_id, "day": str(day), "error": str(exc)[:120]},
                    )
                    return []

        for index, station_id in enumerate(station_ids, start=1):
            results = await asyncio.gather(*(fetch(station_id, day) for day in days))
            station_records = [r for batch in results for r in batch]
            if parameter:
                station_records = [r for r in station_records if r.parameter == parameter]

            if not station_records:
                continue

            totals["stations_with_data"] += 1
            totals["records"] += len(station_records)

            async with factory() as session:
                stored = await store_archive_records(session, station_records)
                await session.commit()
            totals["stored"] += stored
            print(
                f"      [{index:>3}/{len(station_ids)}] station {station_id:<8} "
                f"{len(station_records):>6,} records -> {stored:>6,} rows"
            )

    return totals


async def ingest_fires(start: dt.date, end: dt.date) -> dict[str, int]:
    """Download and store fire detections for the window."""
    settings = get_settings()
    client = FirmsClient(settings.nasa_firms_api_key or "")
    factory = get_session_factory()

    totals = {"detections": 0, "stored": 0}
    for offset in range((end - start).days + 1):
        day = start + dt.timedelta(days=offset)
        source = await client.source_for(day)
        records = await client.fetch_area_day(STUBBLE_BBOX, day, source=source)
        totals["detections"] += len(records)
        if records:
            async with factory() as session:
                totals["stored"] += await store_fire_records(session, records)
                await session.commit()
        logger.info(
            "fires ingested",
            extra={"day": str(day), "source": source, "detections": len(records)},
        )
    return totals


async def ingest_weather(start: dt.date, end: dt.date) -> dict[str, int]:
    """Download and store weather for the window."""
    lat, lon = DELHI_CENTRE
    records = await OpenMeteoArchive().fetch(lat, lon, start, end)
    _write_raw(f"open_meteo_{_stamp(start)}_{_stamp(end)}.json", [asdict(r) for r in records])

    factory = get_session_factory()
    async with factory() as session:
        stored = await store_weather_records(session, records)
        await session.commit()
    return {"hours": len(records), "stored": stored}


async def validate_stored(parameter: str, start: dt.date, end: dt.date) -> int:
    """Validate what was stored, and print a report per station."""
    factory = get_session_factory()
    lo = dt.datetime.combine(start, dt.time.min, tzinfo=dt.UTC)
    hi = dt.datetime.combine(end + dt.timedelta(days=1), dt.time.min, tzinfo=dt.UTC)

    async with factory() as session:
        rows = (
            await session.execute(
                select(Station.name, Measurement.measured_at, Measurement.value)
                .join(Measurement, Measurement.station_id == Station.id)
                .where(
                    Measurement.parameter == parameter,
                    Measurement.measured_at >= lo,
                    Measurement.measured_at < hi,
                )
                .order_by(Station.name, Measurement.measured_at)
            )
        ).all()

    by_station: dict[str, list[tuple[dt.datetime, float]]] = {}
    for name, stamp, value in rows:
        by_station.setdefault(name, []).append((stamp, value))

    print(f"\n{'─' * 78}\nVALIDATION — {parameter}, {start} to {end}\n{'─' * 78}")
    errors = 0
    for name, points in sorted(by_station.items()):
        report = validate_series(name, parameter, points)
        flag = "OK  " if report.ok else "FAIL"
        interval = (
            f"{report.median_interval_minutes:.0f}min" if report.median_interval_minutes else "n/a"
        )
        complete = (
            f"{report.completeness_pct:.0f}%" if report.completeness_pct is not None else "n/a"
        )
        print(
            f"  [{flag}] {name[:40]:42s} n={report.total_records:5d} every {interval:>7s} {complete:>5s}"
        )
        for finding in report.findings:
            if finding.severity != Severity.INFO:
                print(f"         └ {finding.severity.value}: {finding.message}")
        if not report.ok:
            errors += 1
    return errors


async def report_query(parameter: str = "pm25") -> None:
    """Query the stored data — proof the pipeline produced something usable."""
    factory = get_session_factory()
    async with factory() as session:
        stations = (await session.execute(select(func.count()).select_from(Station))).scalar_one()
        measurements = (
            await session.execute(select(func.count()).select_from(Measurement))
        ).scalar_one()
        fires = (
            await session.execute(select(func.count()).select_from(FireDetection))
        ).scalar_one()
        weather = (
            await session.execute(select(func.count()).select_from(WeatherObservation))
        ).scalar_one()

        print(f"\n{'─' * 78}\nSTORED\n{'─' * 78}")
        print(f"  stations {stations:>8,}   measurements {measurements:>9,}")
        print(f"  fires    {fires:>8,}   weather      {weather:>9,}")

        if not measurements:
            return

        # The money query: Diwali night in IST, hour by hour, with fires that day.
        print(f"\n{'─' * 78}\nDIWALI 2019 — Delhi mean {parameter} by hour (IST)\n{'─' * 78}")
        rows = (
            await session.execute(
                select(
                    func.date_trunc("hour", Measurement.measured_at).label("h"),
                    func.avg(Measurement.value).label("mean"),
                    func.max(Measurement.value).label("peak"),
                    func.count(func.distinct(Measurement.station_id)).label("n"),
                )
                .where(
                    Measurement.parameter == parameter,
                    Measurement.measured_at >= dt.datetime(2019, 10, 26, 18, 30, tzinfo=dt.UTC),
                    Measurement.measured_at < dt.datetime(2019, 10, 28, 18, 30, tzinfo=dt.UTC),
                )
                .group_by("h")
                .order_by("h")
            )
        ).all()

        for hour, mean, peak, n in rows:
            ist = hour.astimezone(IST)
            bar = "█" * int(min(60, (mean or 0) / 12))
            print(f"  {ist:%d %b %H:%M} IST  mean {mean:6.1f}  peak {peak:6.1f}  n={n:2d}  {bar}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


async def run_event(args: argparse.Namespace) -> int:
    window = EVENTS.get(args.command)
    if window is None:
        print(f"unknown event: {args.command}")
        return 1
    ev_start, ev_end, note = window
    print(f"{args.command}: {ev_start} .. {ev_end}   ({note})")
    start = ev_start
    end = ev_end if args.days is None else ev_start + dt.timedelta(days=args.days - 1)

    if args.station:
        station_ids = [args.station]
        print(f"vertical slice: station {args.station}, {args.parameter or 'all'}, {start}..{end}")
    else:
        station_ids = await discover_delhi_stations()
        print(f"full event: {len(station_ids)} Delhi stations, {start}..{end}")

    print("\n[1/4] measurements ...")
    m = await ingest_measurements(station_ids, start, end, args.parameter)
    print(
        f"      {m['records']:,} records from {m['stations_with_data']} stations -> {m['stored']:,} stored"
    )
    if m["records"] == 0:
        print("      ERROR: no measurements. The window or station has no archive data.")
        return 1

    if not args.skip_fires:
        print("\n[2/4] fires ...")
        f = await ingest_fires(start, end)
        print(f"      {f['detections']:,} detections -> {f['stored']:,} stored")

    if not args.skip_weather:
        print("\n[3/4] weather ...")
        w = await ingest_weather(start, end)
        print(f"      {w['hours']:,} hours -> {w['stored']:,} stored")

    # One pass over all stations, once ingest is done.
    async with get_session_factory()() as session:
        await refresh_station_extents(session)
        await session.commit()

    print("\n[4/4] validate ...")
    errors = await validate_stored(args.parameter or "pm25", start, end)

    await report_query(args.parameter or "pm25")
    if errors:
        print(f"\n{errors} station(s) failed validation.")
    return 0


async def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    for name, (_ev_s, _ev_e, note) in EVENTS.items():
        ev = sub.add_parser(name, help=f"Ingest {name} end-to-end ({note}).")
        ev.add_argument(
            "--station", type=int, default=None, help=f"One location id, e.g. {DEFAULT_STATION}."
        )
        ev.add_argument("--parameter", default=None, help="One pollutant, e.g. pm25.")
        ev.add_argument(
            "--days", type=int, default=None, help="Days from the window start. Omit for all."
        )
        ev.add_argument("--skip-fires", action="store_true")
        ev.add_argument("--skip-weather", action="store_true")

    q = sub.add_parser("query", help="Report what is stored.")
    q.add_argument("--parameter", default="pm25")

    args = parser.parse_args()
    settings = get_settings()
    configure_logging(level="INFO", log_format="console")

    if settings.database_dsn is None:
        print("DATABASE_URL is not set. See .env.example.")
        return 1

    try:
        if args.command in EVENTS:
            return await run_event(args)
        await report_query(args.parameter)
        return 0
    finally:
        await dispose_engine()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
