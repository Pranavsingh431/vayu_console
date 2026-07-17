"""Shared model building blocks.

Every ingested row records where it came from and when it arrived. Phase 3 has to
defend each number to a municipal officer, and a value with no provenance cannot
be defended — so provenance is a column, not an afterthought.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum

from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

# WGS84. Everything spatial is stored in 4326; reproject at query time if needed.
SRID = 4326


class DataSource(StrEnum):
    """Where a row came from.

    These are distinct measurements, not interchangeable feeds. `DATA_GOV_LIVE`
    carries hourly min/max/avg aggregates; `OPENAQ_S3` carries raw irregular
    readings. Joining them into one series without saying so would be dishonest,
    so the source travels with the row.
    """

    DATA_GOV_LIVE = "data_gov_live"
    OPENAQ_S3 = "openaq_s3"
    OPENAQ_V3_META = "openaq_v3_meta"
    OPEN_METEO_ARCHIVE = "open_meteo_archive"
    FIRMS_VIIRS_SNPP_SP = "firms_viirs_snpp_sp"
    FIRMS_VIIRS_SNPP_NRT = "firms_viirs_snpp_nrt"
    FIRMS_MODIS_SP = "firms_modis_sp"
    FIRMS_MODIS_NRT = "firms_modis_nrt"


class ProvenanceMixin:
    """Columns answering: where did this row come from, and when did we fetch it?"""

    source: Mapped[str] = mapped_column(
        String(40),
        nullable=False,
        index=True,
        doc="DataSource value. Rows from different sources are not interchangeable.",
    )
    ingested_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        doc="When this row entered our database, not when it was observed.",
    )
