"""Assembles an EvidenceContext from stored data.

All the engine's I/O lives here, so modules stay pure and unit-testable. This is
the only place in `app/evidence` that touches a database session.
"""

from __future__ import annotations

import datetime as dt
import logging
import math

from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.evidence.base import EvidenceContext, FireObservation
from app.evidence.biomass.module import LOOKBACK_HOURS, MAX_INFLUENCE_KM
from app.models import Measurement, Station, WeatherObservation

logger = logging.getLogger(__name__)

# How far either side of the requested instant to accept a reading. Sampling is
# irregular (~15 min, with gaps), so demanding an exact hour would return nothing.
MEASUREMENT_TOLERANCE = dt.timedelta(minutes=30)

# Weather is hourly; accept the nearest hour.
WEATHER_TOLERANCE = dt.timedelta(minutes=90)


def _bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Initial bearing from point 1 to point 2, degrees clockwise from north."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    y = math.sin(dl) * math.cos(p2)
    x = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(y, x)) + 360.0) % 360.0


def _bearing_offset(wind_from_deg: float | None, fire_bearing_deg: float) -> float | None:
    """Angle between where the wind comes FROM and where the fire IS.

    Meteorological wind direction is the direction the wind blows *from*, so a
    fire lying in that direction is upwind and its smoke travels toward us. An
    offset of 0 means perfectly upwind; 180 means downwind.
    """
    if wind_from_deg is None:
        return None
    diff = abs((fire_bearing_deg - wind_from_deg + 180.0) % 360.0 - 180.0)
    return diff


class ContextBuilder:
    """Reads stored observations into an EvidenceContext."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def build(self, station_id: int, at: dt.datetime) -> EvidenceContext | None:
        """Assemble the context, or None when the station does not exist."""
        station = (
            await self._session.execute(
                select(
                    Station.id,
                    Station.name,
                    func.ST_Y(Station.geom).label("lat"),
                    func.ST_X(Station.geom).label("lon"),
                ).where(Station.id == station_id)
            )
        ).one_or_none()
        if station is None:
            return None

        pollutants = await self._pollutants(station_id, at)
        weather = await self._weather(station.lat, station.lon, at)
        fires, queried = await self._fires(
            station.lat, station.lon, at, weather.get("wind_direction_deg")
        )

        return EvidenceContext(
            station_name=station.name,
            station_id=station.id,
            evaluated_at=at,
            latitude=station.lat,
            longitude=station.lon,
            pollutants=pollutants,
            fires=fires,
            fires_queried=queried,
            wind_speed_ms=weather["wind_speed_ms"],
            wind_direction_deg=weather["wind_direction_deg"],
            boundary_layer_height_m=weather["boundary_layer_height_m"],
            temperature_c=weather["temperature_c"],
            relative_humidity_pct=weather["relative_humidity_pct"],
        )

    async def _pollutants(self, station_id: int, at: dt.datetime) -> dict[str, float]:
        """Mean of each pollutant within tolerance of the instant.

        Negatives are excluded in SQL: the archive carries -999 sentinels and CO
        values near -476300, and a mean including one is garbage.
        """
        rows = (
            await self._session.execute(
                select(Measurement.parameter, func.avg(Measurement.value))
                .where(
                    Measurement.station_id == station_id,
                    Measurement.value >= 0,
                    Measurement.measured_at >= at - MEASUREMENT_TOLERANCE,
                    Measurement.measured_at <= at + MEASUREMENT_TOLERANCE,
                )
                .group_by(Measurement.parameter)
            )
        ).all()
        return {p: float(v) for p, v in rows if v is not None}

    async def _weather(self, lat: float, lon: float, at: dt.datetime) -> dict[str, float | None]:
        """Nearest weather observation in space and time."""
        row = (
            await self._session.execute(
                select(
                    WeatherObservation.wind_speed_ms,
                    WeatherObservation.wind_direction_deg,
                    WeatherObservation.boundary_layer_height_m,
                    WeatherObservation.temperature_c,
                    WeatherObservation.relative_humidity_pct,
                )
                .where(
                    WeatherObservation.observed_at >= at - WEATHER_TOLERANCE,
                    WeatherObservation.observed_at <= at + WEATHER_TOLERANCE,
                )
                .order_by(
                    func.ST_Distance(
                        WeatherObservation.geom,
                        func.ST_SetSRID(func.ST_MakePoint(lon, lat), 4326),
                    )
                )
                .limit(1)
            )
        ).one_or_none()
        if row is None:
            return dict.fromkeys(
                (
                    "wind_speed_ms",
                    "wind_direction_deg",
                    "boundary_layer_height_m",
                    "temperature_c",
                    "relative_humidity_pct",
                ),
                None,
            )
        return {
            "wind_speed_ms": row.wind_speed_ms,
            "wind_direction_deg": row.wind_direction_deg,
            "boundary_layer_height_m": row.boundary_layer_height_m,
            "temperature_c": row.temperature_c,
            "relative_humidity_pct": row.relative_humidity_pct,
        }

    async def _fires(
        self, lat: float, lon: float, at: dt.datetime, wind_from_deg: float | None
    ) -> tuple[list[FireObservation], bool]:
        """Fire detections within range and lookback, resolved against the station.

        Returns `(fires, queried)`. `queried=True` with an empty list means FIRMS
        looked and found nothing — evidence against biomass. That is a different
        statement from "we did not look", which is what `queried=False` means.
        """
        rows = (
            await self._session.execute(
                text("""
            select ST_Y(geom) lat, ST_X(geom) lon, acquired_at, frp_mw, confidence, source,
                   ST_DistanceSphere(geom, ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)) / 1000.0 dist_km
            from fire_detections
            where acquired_at >= :since and acquired_at <= :at
              and ST_DWithin(geom::geography,
                             ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
                             :radius_m)
            """),
                {
                    "lat": lat,
                    "lon": lon,
                    "at": at,
                    "since": at - dt.timedelta(hours=LOOKBACK_HOURS),
                    "radius_m": MAX_INFLUENCE_KM * 1000.0,
                },
            )
        ).all()

        # Whether any fire data exists for this window at all. Without this check
        # an un-ingested window would look like "no fires burned".
        have_any = (
            await self._session.execute(
                text(
                    "select exists(select 1 from fire_detections "
                    "where acquired_at >= :since and acquired_at <= :at)"
                ),
                {"at": at, "since": at - dt.timedelta(hours=LOOKBACK_HOURS)},
            )
        ).scalar()

        fires = [
            FireObservation(
                latitude=r.lat,
                longitude=r.lon,
                acquired_at=r.acquired_at,
                frp_mw=r.frp_mw,
                confidence=r.confidence,
                distance_km=r.dist_km,
                bearing_offset_deg=_bearing_offset(
                    wind_from_deg, _bearing_deg(lat, lon, r.lat, r.lon)
                ),
                source=r.source,
            )
            for r in rows
        ]
        return fires, bool(have_any)
