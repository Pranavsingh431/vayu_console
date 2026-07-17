"""Sentinels must never reach the database.

Phase 1 stored 5 `-999` values in PM2.5 and CO values near -476300, because
ingestion trusted whatever the CSV said. Every query since has had to remember
`value >= 0`. Dropping them at the source is the only version that stays true.
"""

from __future__ import annotations

import gzip

from app.data.sources.openaq_s3 import OpenAQArchive

HEADER = "location_id,sensors_id,location,datetime,lat,lon,parameter,units,value"


def csv_gz(*rows: str) -> bytes:
    return gzip.compress(("\n".join([HEADER, *rows])).encode())


def row(value: str, parameter: str = "pm25") -> str:
    return f'5541,384,"Burari",2019-10-27T23:30:00+05:30,28.72,77.20,{parameter},µg/m³,{value}'


class TestSentinelFiltering:
    def test_minus_999_is_dropped(self) -> None:
        records = OpenAQArchive._parse(csv_gz(row("-999"), row("312.5")))

        assert [r.value for r in records] == [312.5]

    def test_the_absurd_co_value_is_dropped(self) -> None:
        """-476300 was observed in the real CO series."""
        records = OpenAQArchive._parse(csv_gz(row("-476300", "co"), row("780.0", "co")))

        assert [r.value for r in records] == [780.0]

    def test_any_negative_is_dropped(self) -> None:
        """Negative ozone was observed too. Mass concentration cannot be negative."""
        records = OpenAQArchive._parse(csv_gz(row("-0.7", "so2"), row("-303.4", "o3")))

        assert records == []

    def test_zero_is_kept(self) -> None:
        """Zero is a real reading, not a sentinel."""
        records = OpenAQArchive._parse(csv_gz(row("0")))

        assert [r.value for r in records] == [0.0]

    def test_the_diwali_peak_survives(self) -> None:
        """Filtering must not touch the extreme-but-real values we exist to study."""
        records = OpenAQArchive._parse(csv_gz(row("2660.8")))

        assert [r.value for r in records] == [2660.8]
