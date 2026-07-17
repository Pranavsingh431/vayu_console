"""Monitoring stations and their sensors."""

from __future__ import annotations

import datetime as dt

from geoalchemy2 import Geometry
from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.common import SRID, ProvenanceMixin


class Station(Base, ProvenanceMixin):
    """A physical monitoring location.

    Keyed on OpenAQ's location id, because the S3 archive is partitioned by it
    (`records/csv.gz/locationid={id}/...`) — making it the natural join key
    between metadata discovery and bulk history.
    """

    __tablename__ = "stations"

    id: Mapped[int] = mapped_column(primary_key=True)

    openaq_location_id: Mapped[int | None] = mapped_column(
        BigInteger, unique=True, index=True, doc="OpenAQ location id; the S3 partition key."
    )
    # data.gov.in has no station id — it identifies stations by name alone, so
    # that string is the only key available for reconciling the live feed.
    cpcb_station_name: Mapped[str | None] = mapped_column(String(200), index=True)

    name: Mapped[str] = mapped_column(String(200), nullable=False)
    city: Mapped[str | None] = mapped_column(String(100), index=True)
    provider: Mapped[str | None] = mapped_column(
        String(60), index=True, doc="e.g. CPCB, caaqm, IMD. Provider families differ in liveness."
    )

    geom: Mapped[object] = mapped_column(
        Geometry(geometry_type="POINT", srid=SRID, spatial_index=True),
        nullable=False,
        doc="Station position (lon, lat) in WGS84.",
    )

    # Observed extent of real data, computed from what we actually ingested.
    # Deliberately NOT copied from OpenAQ's datetimeFirst/datetimeLast, which
    # span every sensor at a location and overstate continuous coverage.
    first_observed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    last_observed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    sensors: Mapped[list[Sensor]] = relationship(
        back_populates="station", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_stations_city_provider", "city", "provider"),)


class Sensor(Base, ProvenanceMixin):
    """One instrument measuring one pollutant at one station, over one lifetime.

    A station has several sensors per pollutant across vintages: Anand Vihar
    carries PM2.5 sensor 384 (2016-2018) alongside 12235610 (2025-2026). Modelling
    sensors separately is what stops a query silently reading a decommissioned
    instrument and concluding the station has no data.
    """

    __tablename__ = "sensors"

    id: Mapped[int] = mapped_column(primary_key=True)
    openaq_sensor_id: Mapped[int | None] = mapped_column(BigInteger, unique=True, index=True)

    station_id: Mapped[int] = mapped_column(
        ForeignKey("stations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    parameter: Mapped[str] = mapped_column(
        String(30), nullable=False, index=True, doc="pm25, pm10, no2, so2, co, o3, ..."
    )
    units: Mapped[str | None] = mapped_column(String(20))

    # This sensor's own lifetime — the honest bound on its data.
    datetime_first: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    datetime_last: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))

    station: Mapped[Station] = relationship(back_populates="sensors")

    __table_args__ = (
        UniqueConstraint("station_id", "parameter", "openaq_sensor_id", name="uq_sensor_identity"),
        Index("ix_sensors_param_span", "parameter", "datetime_first", "datetime_last"),
    )
