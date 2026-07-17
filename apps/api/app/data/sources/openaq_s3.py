"""OpenAQ S3 archive — the authoritative source for historical measurements.

**Do not replace this with the OpenAQ v3 measurements API.** That API returns
`0 results` for windows whose data provably exists here: 12 sensors whose metadata
claimed to span Nov 2019 each returned nothing, while the same dates are present as
S3 objects. See docs/phase-1-data-foundation.md §2.3.

The bucket is public — no key, no signing, plain HTTPS.

Layout:
    records/csv.gz/locationid={id}/year={yyyy}/month={mm}/location-{id}-{yyyymmdd}.csv.gz

CSV columns:
    location_id, sensors_id, location, datetime, lat, lon, parameter, units, value
"""

from __future__ import annotations

import csv
import datetime as dt
import gzip
import io
import logging
from dataclasses import dataclass

import httpx

# defusedxml, not the stdlib parser: this XML arrives over the network, and the
# stdlib is vulnerable to entity-expansion attacks on hostile input.
from defusedxml import ElementTree as ET

logger = logging.getLogger(__name__)

BUCKET_URL = "https://openaq-data-archive.s3.amazonaws.com"
_S3_NS = {"s3": "http://s3.amazonaws.com/doc/2006-03-01/"}

# The archive publishes IST; timestamps carry an explicit +05:30 offset.
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))

# Missing-data sentinels the CPCB feed emits as if they were readings. -999 is the
# classic one; values near -476300 were observed in CO. A concentration cannot be
# negative, so ANY negative value is either a sentinel or an instrument fault, and
# neither belongs in a mean.
#
# Dropped at parse time rather than filtered in queries: a sentinel that reaches
# the database is a sentinel that some future query will forget to exclude. Phase
# 1 stored 5 of these in PM2.5 and they had to be excluded by hand at every call
# site since.
SENTINEL_VALUES = frozenset({-999.0, -9999.0})


@dataclass(frozen=True, slots=True)
class ArchiveRecord:
    """One reading from the archive, normalised to UTC."""

    location_id: int
    sensor_id: int | None
    location_name: str
    measured_at: dt.datetime
    latitude: float
    longitude: float
    parameter: str
    units: str | None
    value: float


class OpenAQArchiveError(RuntimeError):
    """The archive could not be read."""


class OpenAQArchive:
    """Reads the public OpenAQ S3 archive."""

    def __init__(self, client: httpx.AsyncClient | None = None, timeout: float = 60.0) -> None:
        self._client = client
        self._timeout = timeout

    async def _get(self, url: str) -> bytes:
        close = False
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=self._timeout)
            close = True
        try:
            response = await client.get(url)
            response.raise_for_status()
            return response.content
        except httpx.HTTPError as exc:
            raise OpenAQArchiveError(f"GET {url} failed: {exc}") from exc
        finally:
            if close:
                await client.aclose()

    async def list_keys(self, location_id: int, year: int, month: int | None = None) -> list[str]:
        """List object keys for a location and period.

        Truncated listings are followed; a busy month can exceed the 1000-key page.
        """
        prefix = f"records/csv.gz/locationid={location_id}/year={year}/"
        if month is not None:
            prefix += f"month={month:02d}/"

        keys: list[str] = []
        token: str | None = None
        while True:
            url = f"{BUCKET_URL}?list-type=2&max-keys=1000&prefix={prefix}"
            if token:
                url += f"&continuation-token={httpx.QueryParams({'t': token})['t']}"
            root = ET.fromstring(await self._get(url))
            keys.extend(k.text for k in root.findall(".//s3:Key", _S3_NS) if k.text)

            truncated = root.find(".//s3:IsTruncated", _S3_NS)
            if truncated is None or truncated.text != "true":
                break
            nxt = root.find(".//s3:NextContinuationToken", _S3_NS)
            if nxt is None or not nxt.text:
                break
            token = nxt.text

        return keys

    async def has_year(self, location_id: int, year: int) -> bool:
        """Whether any data exists for a location in a year.

        Cheap coverage probe: asks for a single key rather than listing the year.
        """
        url = (
            f"{BUCKET_URL}?list-type=2&max-keys=1"
            f"&prefix=records/csv.gz/locationid={location_id}/year={year}/"
        )
        count = ET.fromstring(await self._get(url)).find(".//s3:KeyCount", _S3_NS)
        return count is not None and int(count.text or 0) > 0

    async def fetch_day(self, location_id: int, day: dt.date) -> list[ArchiveRecord]:
        """Fetch one day's readings for one location.

        Returns `[]` when the object is absent — a station simply may not have
        reported that day. Absence is data, not an error.
        """
        key = (
            f"records/csv.gz/locationid={location_id}/year={day.year}/"
            f"month={day.month:02d}/location-{location_id}-{day:%Y%m%d}.csv.gz"
        )
        try:
            raw = await self._get(f"{BUCKET_URL}/{key}")
        except OpenAQArchiveError as exc:
            if "404" in str(exc):
                logger.debug("no archive object", extra={"key": key})
                return []
            raise
        return list(self._parse(raw))

    @staticmethod
    def _parse(raw: bytes) -> list[ArchiveRecord]:
        text = gzip.decompress(raw).decode("utf-8", errors="replace")
        records: list[ArchiveRecord] = []

        for row in csv.DictReader(io.StringIO(text)):
            value = (row.get("value") or "").strip()
            stamp = (row.get("datetime") or "").strip()
            if not value or not stamp:
                continue
            try:
                measured = dt.datetime.fromisoformat(stamp)
                numeric = float(value)
            except ValueError:
                logger.debug("unparseable archive row", extra={"row": row})
                continue

            # A negative concentration is physically impossible. Keeping it would
            # corrupt every aggregate that touches it.
            if numeric < 0 or numeric in SENTINEL_VALUES:
                logger.debug(
                    "dropped sentinel or impossible value",
                    extra={"value": numeric, "parameter": row.get("parameter")},
                )
                continue

            # Rows carry +05:30. Anything naive is IST by convention here; store UTC.
            if measured.tzinfo is None:
                measured = measured.replace(tzinfo=IST)

            records.append(
                ArchiveRecord(
                    location_id=int(row["location_id"]),
                    sensor_id=int(row["sensors_id"]) if row.get("sensors_id") else None,
                    location_name=(row.get("location") or "").strip(),
                    measured_at=measured.astimezone(dt.UTC),
                    latitude=float(row["lat"]),
                    longitude=float(row["lon"]),
                    parameter=(row.get("parameter") or "").strip(),
                    units=(row.get("units") or "").strip() or None,
                    value=numeric,
                )
            )

        return records
