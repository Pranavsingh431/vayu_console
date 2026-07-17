"""Station endpoints. Read-only."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select

from app.api.deps import DbSessionDep
from app.models import Station

router = APIRouter(tags=["stations"])


class StationSummary(BaseModel):
    """A station and where it is. Enough to place it on a map."""

    id: int
    name: str
    latitude: float
    longitude: float
    provider: str | None = Field(
        default=None,
        description=(
            "CPCB stations are reference-grade regulatory monitors; AirGradient are "
            "low-cost sensors with different uncertainty. Not interchangeable."
        ),
    )
    first_observed_at: dt.datetime | None = None
    last_observed_at: dt.datetime | None = None


@router.get("/stations", response_model=list[StationSummary], summary="Delhi monitoring stations")
async def stations(
    session: DbSessionDep,
    at: dt.datetime | None = Query(
        default=None,
        description="Only stations with observations spanning this instant.",
    ),
) -> list[StationSummary]:
    """List stations we hold data for.

    `first_observed_at`/`last_observed_at` are computed from what we actually
    ingested — never copied from OpenAQ's metadata, which spans every sensor at a
    location and would claim coverage across years that contain nothing.
    """
    stmt = select(
        Station.id,
        Station.name,
        func.ST_Y(Station.geom).label("latitude"),
        func.ST_X(Station.geom).label("longitude"),
        Station.provider,
        Station.first_observed_at,
        Station.last_observed_at,
    ).order_by(Station.name)

    if at is not None:
        stmt = stmt.where(
            Station.first_observed_at <= at,
            Station.last_observed_at >= at,
        )

    rows = (await session.execute(stmt)).all()
    return [
        StationSummary(
            id=r.id,
            name=r.name,
            latitude=r.latitude,
            longitude=r.longitude,
            provider=r.provider,
            first_observed_at=r.first_observed_at,
            last_observed_at=r.last_observed_at,
        )
        for r in rows
    ]
