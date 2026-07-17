"""Open-Meteo Archive — ERA5 reanalysis, free and keyless.

This replaces the Copernicus CDS route entirely. Open-Meteo's archive *is* ERA5, so
it delivers the same variables with no second account, no job queue, no GRIB
parsing and no multi-hour latency. Verified returning wind and boundary layer
height for November 2019.

Caveat worth carrying into any inference: an ERA5 cell is ~25 km, so a value
describes the cell containing the point, not the point. Where a station has its own
anemometer, prefer the station.
"""

from __future__ import annotations

import datetime as dt
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

ARCHIVE_URL = "https://archive-api.open-meteo.com/v1/archive"

# boundary_layer_height is the one that decides whether given emissions read as
# 80 or 400 µg/m³; wind_direction is what connects a Punjab fire to a Delhi monitor.
HOURLY_VARIABLES = (
    "temperature_2m",
    "relative_humidity_2m",
    "wind_speed_10m",
    "wind_direction_10m",
    "boundary_layer_height",
    "precipitation",
)


@dataclass(frozen=True, slots=True)
class WeatherRecord:
    """One hour of meteorology at a point."""

    latitude: float
    longitude: float
    observed_at: dt.datetime
    temperature_c: float | None
    relative_humidity_pct: float | None
    wind_speed_ms: float | None
    wind_direction_deg: float | None
    boundary_layer_height_m: float | None
    precipitation_mm: float | None


class OpenMeteoError(RuntimeError):
    """Open-Meteo could not be queried."""


class OpenMeteoArchive:
    """Fetches historical hourly weather."""

    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 60.0) -> None:
        self._client = client
        self._timeout = timeout

    async def fetch(
        self, latitude: float, longitude: float, start: dt.date, end: dt.date
    ) -> list[WeatherRecord]:
        """Fetch hourly weather for a point over an inclusive date range."""
        params: dict[str, str] = {
            "latitude": str(latitude),
            "longitude": str(longitude),
            "start_date": start.isoformat(),
            "end_date": end.isoformat(),
            "hourly": ",".join(HOURLY_VARIABLES),
            # Ask for UTC rather than converting a naive local timestamp ourselves.
            "timezone": "UTC",
            "wind_speed_unit": "ms",
        }

        close = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout)
            close = True
        try:
            response = await client.get(ARCHIVE_URL, params=params)
            response.raise_for_status()
            payload = response.json()
        except httpx.HTTPError as exc:
            raise OpenMeteoError(f"Open-Meteo request failed: {exc}") from exc
        finally:
            if close:
                await client.aclose()

        if "error" in payload:
            raise OpenMeteoError(f"Open-Meteo error: {payload.get('reason')}")

        hourly = payload.get("hourly") or {}
        times = hourly.get("time") or []
        if not times:
            logger.warning(
                "open-meteo returned no hours",
                extra={"lat": latitude, "lon": longitude, "start": str(start), "end": str(end)},
            )
            return []

        def col(name: str) -> list[float | None]:
            return hourly.get(name) or [None] * len(times)

        temps, rh = col("temperature_2m"), col("relative_humidity_2m")
        ws, wd = col("wind_speed_10m"), col("wind_direction_10m")
        blh, precip = col("boundary_layer_height"), col("precipitation")

        # Open-Meteo may snap to its grid; record where the value actually came from.
        lat = float(payload.get("latitude", latitude))
        lon = float(payload.get("longitude", longitude))

        records = []
        for i, stamp in enumerate(times):
            records.append(
                WeatherRecord(
                    latitude=lat,
                    longitude=lon,
                    observed_at=dt.datetime.fromisoformat(stamp).replace(tzinfo=dt.UTC),
                    temperature_c=temps[i],
                    relative_humidity_pct=rh[i],
                    wind_speed_ms=ws[i],
                    wind_direction_deg=wd[i],
                    boundary_layer_height_m=blh[i],
                    precipitation_mm=precip[i],
                )
            )
        return records
