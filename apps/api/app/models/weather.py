"""Weather observations (Open-Meteo Archive / ERA5 reanalysis)."""

from __future__ import annotations

import datetime as dt

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, Float, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import SRID, ProvenanceMixin


class WeatherObservation(Base, ProvenanceMixin):
    """Hourly meteorology at a point.

    Weather is not context here, it is the mechanism: wind direction is what links
    a fire in Punjab to a monitor in Delhi, and boundary layer height is what
    decides whether the same emissions read as 80 or 400 µg/m³.

    ERA5 cells are ~25 km, so a value is a cell average, not a point measurement.
    Where a station has its own anemometer, prefer that.
    """

    __tablename__ = "weather_observations"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    geom: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=SRID, spatial_index=True),
        nullable=False,
        doc="Requested point (lon, lat). The value describes the ~25 km cell containing it.",
    )
    observed_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, doc="Observation hour, UTC."
    )

    temperature_c: Mapped[float | None] = mapped_column(Float)
    relative_humidity_pct: Mapped[float | None] = mapped_column(Float)
    wind_speed_ms: Mapped[float | None] = mapped_column(Float, doc="10 m wind speed.")
    wind_direction_deg: Mapped[float | None] = mapped_column(
        Float, doc="10 m wind direction, meteorological convention: degrees FROM which wind blows."
    )
    boundary_layer_height_m: Mapped[float | None] = mapped_column(
        Float, doc="Mixing depth. Low BLH concentrates the same emissions into less air."
    )
    precipitation_mm: Mapped[float | None] = mapped_column(Float)

    __table_args__ = (
        UniqueConstraint("geom", "observed_at", "source", name="uq_weather_identity"),
        Index("ix_weather_time", "observed_at"),
    )
