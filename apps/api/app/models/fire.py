"""Active fire detections (NASA FIRMS)."""

from __future__ import annotations

import datetime as dt

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, Float, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import SRID, ProvenanceMixin


class FireDetection(Base, ProvenanceMixin):
    """One thermal anomaly detected by a satellite overpass.

    A detection is a fire *observed from orbit*, not a quantity of smoke delivered
    to a ward. Attribution built on these is inference under stated assumptions —
    never measurement. See docs/phase-1-data-foundation.md §5.

    `source` distinguishes SP from NRT because they are different products with
    different processing, not merely different date ranges.
    """

    __tablename__ = "fire_detections"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    geom: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=SRID, spatial_index=True),
        nullable=False,
        doc="Detection centroid (lon, lat), WGS84. Not a point fire — a pixel footprint.",
    )
    acquired_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, doc="Satellite overpass, UTC."
    )

    brightness_k: Mapped[float | None] = mapped_column(
        Float, doc="Brightness temperature (K): bright_ti4 for VIIRS, brightness for MODIS."
    )
    frp_mw: Mapped[float | None] = mapped_column(
        Float, doc="Fire radiative power (MW) — the closest available proxy for intensity."
    )
    # VIIRS reports l/n/h; MODIS reports 0-100. Kept as text rather than coerced,
    # because collapsing two different scales into one number would invent precision.
    confidence: Mapped[str | None] = mapped_column(String(10), index=True)

    satellite: Mapped[str | None] = mapped_column(String(20))
    instrument: Mapped[str | None] = mapped_column(String(20))
    daynight: Mapped[str | None] = mapped_column(String(1), doc="D or N.")

    scan: Mapped[float | None] = mapped_column(Float, doc="Pixel size along scan (km).")
    track: Mapped[float | None] = mapped_column(Float, doc="Pixel size along track (km).")

    __table_args__ = (
        # FIRMS has no detection id, so identity is position + instant + product.
        UniqueConstraint("geom", "acquired_at", "source", name="uq_fire_detection_identity"),
        Index("ix_fire_time", "acquired_at"),
    )
