"""Pollutant measurements."""

from __future__ import annotations

import datetime as dt

from sqlalchemy import BigInteger, DateTime, Float, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base
from app.models.common import ProvenanceMixin


class Measurement(Base, ProvenanceMixin):
    """One pollutant reading, at one instant, from one sensor.

    Timestamps are stored in UTC. The S3 archive publishes IST (+05:30) and its
    daily files run past midnight IST — Diwali's firework peak is at night IST,
    so mishandling this shifts the spike onto the wrong day. Store UTC, present IST.

    Sampling is irregular (00:15, 00:30, 01:00, 01:30, 02:00, 02:15, 02:45 ...),
    not hourly. Nothing here assumes a fixed interval.
    """

    __tablename__ = "measurements"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)

    station_id: Mapped[int] = mapped_column(
        ForeignKey("stations.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sensor_id: Mapped[int | None] = mapped_column(
        ForeignKey("sensors.id", ondelete="SET NULL"), index=True
    )

    parameter: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    value: Mapped[float] = mapped_column(Float, nullable=False)
    units: Mapped[str | None] = mapped_column(String(20))

    measured_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True, doc="Observation instant, UTC."
    )

    __table_args__ = (
        # Re-running an ingest must not duplicate rows. The natural key is
        # (station, parameter, instant, source): the same reading from the live
        # feed and from the archive are different measurements and both may exist.
        UniqueConstraint(
            "station_id", "parameter", "measured_at", "source", name="uq_measurement_identity"
        ),
        # The dominant query is "this pollutant, this station, this window".
        Index("ix_measurements_station_param_time", "station_id", "parameter", "measured_at"),
        Index("ix_measurements_param_time", "parameter", "measured_at"),
    )
