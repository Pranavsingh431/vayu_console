"""NASA FIRMS — active fire detections.

The trap this module exists to prevent: **the `*_NRT` sources return 0 rows for any
historical date, without erroring.** `VIIRS_SNPP_NRT` only begins 2026-04-28.
Hardcoding a source name yields zero fires for every natural experiment and no
indication anything is wrong.

Sources are therefore chosen by the requested date, against the availability
windows FIRMS itself publishes. Verified 2026-07-17:

    MODIS_SP         2000-11-01 .. 2026-04-30
    VIIRS_SNPP_SP    2012-01-20 .. 2026-04-27   <- primary history
    VIIRS_NOAA20_SP  2018-04-01 .. 2026-04-30
    VIIRS_SNPP_NRT   2026-04-28 .. current
    MODIS_NRT        2026-05-01 .. current

Quota: 5,000 transactions / 10 minutes; a multi-day request may count as several.
"""

from __future__ import annotations

import csv
import datetime as dt
import io
import logging
from dataclasses import dataclass

import httpx

logger = logging.getLogger(__name__)

API_BASE = "https://firms.modaps.eosdis.nasa.gov/api"


@dataclass(frozen=True, slots=True)
class FireRecord:
    """One thermal anomaly from one satellite overpass."""

    latitude: float
    longitude: float
    acquired_at: dt.datetime
    brightness_k: float | None
    frp_mw: float | None
    confidence: str | None
    satellite: str | None
    instrument: str | None
    daynight: str | None
    scan: float | None
    track: float | None
    source: str


@dataclass(frozen=True, slots=True)
class SourceWindow:
    """A FIRMS product and the dates it covers."""

    data_id: str
    min_date: dt.date
    max_date: dt.date

    def covers(self, day: dt.date) -> bool:
        return self.min_date <= day <= self.max_date


class FirmsError(RuntimeError):
    """FIRMS could not be queried."""


class FirmsClient:
    """Queries NASA FIRMS, choosing the product that actually covers the date."""

    # Preference order among products covering a date. VIIRS resolves ~375 m
    # against MODIS's ~1 km, which matters for counting individual field fires.
    _PREFERENCE = ("VIIRS_SNPP_SP", "VIIRS_NOAA20_SP", "VIIRS_SNPP_NRT", "MODIS_SP", "MODIS_NRT")

    def __init__(
        self, map_key: str, client: httpx.AsyncClient | None = None, timeout: float = 90.0
    ):
        if not map_key:
            raise FirmsError("NASA_FIRMS_API_KEY is not set.")
        self._key = map_key
        self._client = client
        self._timeout = timeout
        self._windows: list[SourceWindow] | None = None

    async def _get(self, url: str) -> str:
        close = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout)
            close = True
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.text
        except httpx.HTTPError as exc:
            raise FirmsError(f"GET {url.replace(self._key, '***')} failed: {exc}") from exc
        finally:
            if close:
                await client.aclose()

    async def availability(self) -> list[SourceWindow]:
        """Fetch each product's coverage window from FIRMS.

        Queried rather than hardcoded: NRT windows roll forward daily, and a stale
        constant would silently reintroduce the empty-history bug.
        """
        if self._windows is not None:
            return self._windows

        text = await self._get(f"{API_BASE}/data_availability/csv/{self._key}/all")
        windows: list[SourceWindow] = []
        for row in csv.DictReader(io.StringIO(text)):
            try:
                windows.append(
                    SourceWindow(
                        data_id=row["data_id"].strip(),
                        min_date=dt.date.fromisoformat(row["min_date"].strip()),
                        max_date=dt.date.fromisoformat(row["max_date"].strip()),
                    )
                )
            except (KeyError, ValueError):
                continue

        if not windows:
            raise FirmsError("FIRMS returned no availability windows; is the map key valid?")
        self._windows = windows
        return windows

    async def source_for(self, day: dt.date) -> str:
        """The best product covering `day`.

        Raises rather than falling back to a product that would return an empty
        CSV: silence here is what makes the failure invisible.
        """
        covering = {w.data_id for w in await self.availability() if w.covers(day)}
        for candidate in self._PREFERENCE:
            if candidate in covering:
                return candidate
        raise FirmsError(
            f"No FIRMS product covers {day}. Available: "
            + ", ".join(
                f"{w.data_id}[{w.min_date}..{w.max_date}]" for w in await self.availability()
            )
        )

    async def fetch_area_day(
        self, bbox: tuple[float, float, float, float], day: dt.date, source: str | None = None
    ) -> list[FireRecord]:
        """Fetch detections in `bbox` (west, south, east, north) for one day."""
        source = source or await self.source_for(day)
        west, south, east, north = bbox
        url = (
            f"{API_BASE}/area/csv/{self._key}/{source}/"
            f"{west},{south},{east},{north}/1/{day:%Y-%m-%d}"
        )
        text = await self._get(url)

        if text.lstrip().lower().startswith(("invalid", "error")):
            raise FirmsError(f"FIRMS rejected the request: {text[:120]}")

        records = [
            r
            for r in (self._parse_row(row, source) for row in csv.DictReader(io.StringIO(text)))
            if r
        ]
        logger.info(
            "firms fetch complete",
            extra={"source": source, "day": str(day), "detections": len(records)},
        )
        return records

    @staticmethod
    def _parse_row(row: dict[str, str], source: str) -> FireRecord | None:
        try:
            # acq_time is HHMM, zero-stripped: "736" means 07:36 UTC.
            acq = row["acq_time"].strip().zfill(4)
            stamp = dt.datetime.strptime(f"{row['acq_date'].strip()} {acq}", "%Y-%m-%d %H%M")
            stamp = stamp.replace(tzinfo=dt.UTC)
        except (KeyError, ValueError):
            logger.debug("unparseable firms row", extra={"row": row})
            return None

        def num(*names: str) -> float | None:
            for n in names:
                v = (row.get(n) or "").strip()
                if v:
                    try:
                        return float(v)
                    except ValueError:
                        return None
            return None

        return FireRecord(
            latitude=float(row["latitude"]),
            longitude=float(row["longitude"]),
            acquired_at=stamp,
            # VIIRS calls it bright_ti4; MODIS calls it brightness.
            brightness_k=num("bright_ti4", "brightness"),
            frp_mw=num("frp"),
            # VIIRS: l/n/h. MODIS: 0-100. Left as text — one scale is not the other.
            confidence=(row.get("confidence") or "").strip() or None,
            satellite=(row.get("satellite") or "").strip() or None,
            instrument=(row.get("instrument") or "").strip() or None,
            daynight=(row.get("daynight") or "").strip() or None,
            scan=num("scan"),
            track=num("track"),
            source=source,
        )
