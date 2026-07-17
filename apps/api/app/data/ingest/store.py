"""Persisting source records.

Every write is an idempotent upsert keyed on the natural identity declared in the
migration. Re-running `download_data.py` must not duplicate rows — during a sprint
the same command gets run many times, and a pipeline that double-counts on the
second run is worse than one that fails.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any, cast

from geoalchemy2.functions import ST_SetSRID
from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.data.sources.firms import FireRecord
from app.data.sources.open_meteo import WeatherRecord
from app.data.sources.openaq_s3 import ArchiveRecord
from app.models import FireDetection, Measurement, Sensor, Station, WeatherObservation
from app.models.common import SRID, DataSource

logger = logging.getLogger(__name__)

# Rows per INSERT. Sized so a batch completes well inside the statement timeout:
# at 1000 the upsert-with-RETURNING was cancelled part-way through a full ingest.
CHUNK_SIZE = 500


def _point(longitude: float, latitude: float):  # type: ignore[no-untyped-def]
    """A PostGIS POINT. Note the order: longitude first, then latitude."""
    return ST_SetSRID(func.ST_MakePoint(longitude, latitude), SRID)


async def upsert_station_from_archive(
    session: AsyncSession, record: ArchiveRecord, city: str = "Delhi"
) -> int:
    """Ensure a station row exists for an archive record; return its id."""
    stmt = (
        insert(Station)
        .values(
            openaq_location_id=record.location_id,
            name=record.location_name or f"location-{record.location_id}",
            city=city,
            geom=_point(record.longitude, record.latitude),
            source=DataSource.OPENAQ_S3.value,
        )
        .on_conflict_do_update(
            index_elements=["openaq_location_id"],
            set_={"name": record.location_name or f"location-{record.location_id}"},
        )
        .returning(Station.id)
    )
    return (await session.execute(stmt)).scalar_one()


async def upsert_sensor(
    session: AsyncSession, station_id: int, record: ArchiveRecord
) -> int | None:
    """Ensure a sensor row exists; return its id.

    Sensors are tracked individually because a station carries several per
    pollutant across vintages — conflating them is how a query ends up reading a
    decommissioned instrument.
    """
    if record.sensor_id is None:
        return None
    stmt = (
        insert(Sensor)
        .values(
            openaq_sensor_id=record.sensor_id,
            station_id=station_id,
            parameter=record.parameter,
            units=record.units,
            source=DataSource.OPENAQ_S3.value,
        )
        .on_conflict_do_update(index_elements=["openaq_sensor_id"], set_={"units": record.units})
        .returning(Sensor.id)
    )
    return (await session.execute(stmt)).scalar_one()


async def store_archive_records(
    session: AsyncSession, records: list[ArchiveRecord], city: str = "Delhi"
) -> int:
    """Store archive readings. Returns the number of rows written or updated."""
    if not records:
        return 0

    station_ids: dict[int, int] = {}
    sensor_ids: dict[int, int | None] = {}

    for record in records:
        if record.location_id not in station_ids:
            station_ids[record.location_id] = await upsert_station_from_archive(
                session, record, city
            )
        key = record.sensor_id
        if key is not None and key not in sensor_ids:
            sensor_ids[key] = await upsert_sensor(session, station_ids[record.location_id], record)

    rows = [
        {
            "station_id": station_ids[r.location_id],
            "sensor_id": sensor_ids.get(r.sensor_id) if r.sensor_id else None,
            "parameter": r.parameter,
            "value": r.value,
            "units": r.units,
            "measured_at": r.measured_at,
            "source": DataSource.OPENAQ_S3.value,
        }
        for r in records
    ]

    written = 0
    # Chunked: a busy month is tens of thousands of rows, and one giant statement
    # risks exceeding the pooler's limits.
    for start in range(0, len(rows), CHUNK_SIZE):
        chunk = rows[start : start + CHUNK_SIZE]
        stmt = (
            insert(Measurement)
            .values(chunk)
            .on_conflict_do_update(
                constraint="uq_measurement_identity",
                set_={"value": insert(Measurement).excluded.value},
            )
            # RETURNING, not rowcount: psycopg3 reports -1 for a chunked upsert,
            # which silently sums into a negative "rows written" count.
            .returning(Measurement.id)
        )
        written += len((await session.execute(stmt)).scalars().all())

    return written


async def refresh_station_extents(session: AsyncSession) -> int:
    """Recompute every station's observed extent from stored rows, in one pass.

    Derived from what we actually hold, never copied from OpenAQ's
    datetimeFirst/datetimeLast — those span every sensor at a location and would
    claim continuous coverage across years that contain nothing.

    Called once after ingest rather than per station: as a scan-per-station inside
    each write transaction it grew with the table and eventually tripped the
    statement timeout.
    """
    extents = (
        select(
            Measurement.station_id.label("sid"),
            func.min(Measurement.measured_at).label("first_at"),
            func.max(Measurement.measured_at).label("last_at"),
        )
        .group_by(Measurement.station_id)
        .subquery()
    )
    # session.execute is typed as returning Result; an UPDATE always yields a
    # CursorResult, which is the only thing carrying rowcount.
    result = cast(
        "CursorResult[Any]",
        await session.execute(
            update(Station)
            .where(Station.id == extents.c.sid)
            .values(first_observed_at=extents.c.first_at, last_observed_at=extents.c.last_at)
        ),
    )
    return result.rowcount or 0


async def store_fire_records(session: AsyncSession, records: list[FireRecord]) -> int:
    """Store fire detections."""
    if not records:
        return 0
    written = 0
    for start in range(0, len(records), CHUNK_SIZE):
        chunk = records[start : start + CHUNK_SIZE]
        rows = [
            {
                "geom": _point(r.longitude, r.latitude),
                "acquired_at": r.acquired_at,
                "brightness_k": r.brightness_k,
                "frp_mw": r.frp_mw,
                "confidence": r.confidence,
                "satellite": r.satellite,
                "instrument": r.instrument,
                "daynight": r.daynight,
                "scan": r.scan,
                "track": r.track,
                "source": f"firms_{r.source.lower()}",
            }
            for r in chunk
        ]
        stmt = (
            insert(FireDetection)
            .values(rows)
            .on_conflict_do_nothing(constraint="uq_fire_detection_identity")
            .returning(FireDetection.id)
        )
        written += len((await session.execute(stmt)).scalars().all())
    return written


async def store_weather_records(session: AsyncSession, records: list[WeatherRecord]) -> int:
    """Store weather observations."""
    if not records:
        return 0
    rows = [
        {
            "geom": _point(r.longitude, r.latitude),
            "observed_at": r.observed_at,
            "temperature_c": r.temperature_c,
            "relative_humidity_pct": r.relative_humidity_pct,
            "wind_speed_ms": r.wind_speed_ms,
            "wind_direction_deg": r.wind_direction_deg,
            "boundary_layer_height_m": r.boundary_layer_height_m,
            "precipitation_mm": r.precipitation_mm,
            "source": DataSource.OPEN_METEO_ARCHIVE.value,
        }
        for r in records
    ]
    stmt = (
        insert(WeatherObservation)
        .values(rows)
        .on_conflict_do_nothing(constraint="uq_weather_identity")
        .returning(WeatherObservation.id)
    )
    return len((await session.execute(stmt)).scalars().all())


async def count_measurements(
    session: AsyncSession, parameter: str | None = None, since: dt.datetime | None = None
) -> int:
    """Count stored measurements, optionally filtered."""
    stmt = select(func.count()).select_from(Measurement)
    if parameter:
        stmt = stmt.where(Measurement.parameter == parameter)
    if since:
        stmt = stmt.where(Measurement.measured_at >= since)
    return (await session.execute(stmt)).scalar_one()
