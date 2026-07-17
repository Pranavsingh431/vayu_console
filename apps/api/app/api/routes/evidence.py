"""Evidence Engine endpoints. Read-only."""

from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.api.deps import DbSessionDep
from app.evidence import ENGINE_VERSION, EvidenceAggregator, EvidenceContext, FireObservation
from app.evidence.schemas.evidence import EvidenceReport
from app.evidence.services.context_builder import ContextBuilder

router = APIRouter(prefix="/evidence", tags=["evidence"])

# Diwali 2019, 23:30 IST at Anand Vihar — the Phase 1 gate, and the case the
# engine exists for: a firework spike confounded with 1,604 upwind stubble fires.
_EXAMPLE_AT = dt.datetime(2019, 10, 27, 18, 0, tzinfo=dt.UTC)


class EvaluateRequest(BaseModel):
    """Which station-hour to explain."""

    station_id: int = Field(description="Station id, from GET /stations.")
    at: dt.datetime = Field(description="The instant to explain, ISO 8601. UTC assumed if naive.")


class ModuleInfo(BaseModel):
    """What a module is, and how far it can be trusted."""

    name: str
    hypothesis: str
    identification: str
    identification_note: str


_IDENTIFICATION_NOTES: dict[str, str] = {
    "biomass": (
        "Strongly identified. FIRMS observes fires from orbit, independently of the "
        "air-quality monitor being explained, so the evidence is exogenous."
    ),
    "traffic": (
        "Weakly identified. No signal exists outside the chemistry being explained. "
        "Calibrated against the COVID lockdown (NO2 -51.5%, SO2 -6.6%), which "
        "measured a likelihood ratio of 1.93 — weak. Lockdown also halted "
        "construction and industry, so that ratio is an upper bound."
    ),
    "industrial": (
        "Very weakly identified. No natural experiment isolates industry, so this "
        "module carries no likelihood ratio. SO2 is measured at 36 of 96 stations; "
        "elsewhere the module is blind and says so."
    ),
}


def _example_context() -> EvidenceContext:
    """A fixed, self-contained context. Needs no database, so /example always works."""
    return EvidenceContext(
        station_name="Anand Vihar (example)",
        station_id=None,
        evaluated_at=_EXAMPLE_AT,
        latitude=28.6469,
        longitude=77.3161,
        pollutants={"no2": 64.0, "so2": 11.0, "pm25": 1288.0, "pm10": 1802.0},
        wind_speed_ms=4.0,
        wind_direction_deg=315.0,
        boundary_layer_height_m=210.0,
        temperature_c=21.0,
        fires_queried=True,
        fires=[
            FireObservation(
                latitude=30.2 + (i % 7) * 0.05,
                longitude=76.4 + (i % 5) * 0.05,
                acquired_at=_EXAMPLE_AT - dt.timedelta(hours=6 + (i % 4)),
                frp_mw=20.0 + (i % 9) * 8.0,
                confidence="h" if i % 3 else "n",
                distance_km=195.0 + (i % 11) * 4.0,
                bearing_offset_deg=5.0 + (i % 13) * 3.0,
                source="firms_viirs_snpp_sp",
            )
            for i in range(28)
        ],
    )


@router.get(
    "/example",
    response_model=EvidenceReport,
    summary="A worked evidence report (Diwali 2019, Anand Vihar)",
)
async def evidence_example() -> EvidenceReport:
    """Return a fixed example report.

    Uses a hard-coded context rather than the database, so it demonstrates the
    contract even on a fresh clone with nothing ingested.
    """
    return EvidenceAggregator().evaluate(_example_context())


@router.get("/modules", response_model=list[ModuleInfo], summary="Registered evidence modules")
async def evidence_modules() -> list[ModuleInfo]:
    """List the modules and how far each is identified by the available data."""
    return [
        ModuleInfo(
            name=m.name,
            hypothesis=str(m.hypothesis),
            identification=str(m.identification),
            identification_note=_IDENTIFICATION_NOTES.get(m.name, ""),
        )
        for m in EvidenceAggregator().modules
    ]


@router.get("/history", summary="Falsification results per module")
async def evidence_history() -> dict[str, object]:
    """Report each module's natural-experiment tests and their outcomes.

    Sourced from a live evaluation rather than a static table, so it cannot drift
    away from what the modules actually claim.
    """
    report = EvidenceAggregator().evaluate(_example_context())
    return {
        "engine_version": ENGINE_VERSION,
        "note": (
            "A module is deleted from the product if a test rejects it. Falsification "
            "needs no minimum n: one decisive test kills a hypothesis."
        ),
        "modules": [
            {
                "name": e.name,
                "hypothesis": str(e.hypothesis),
                "identification": str(e.identification),
                "validations": [v.model_dump(mode="json") for v in e.historical_validation],
            }
            for e in report.evidence
        ],
    }


@router.post(
    "/evaluate",
    response_model=EvidenceReport,
    summary="Evidence report for a station and time",
)
async def evidence_evaluate(request: EvaluateRequest, session: DbSessionDep) -> EvidenceReport:
    """Build a full evidence report from stored observations.

    Returns 404 for an unknown station. A station that exists but has no data at
    the requested instant returns a report of `insufficient_evidence`, not an
    error — "we cannot see" is a finding, not a failure.
    """
    at = request.at if request.at.tzinfo else request.at.replace(tzinfo=dt.UTC)

    context = await ContextBuilder(session).build(request.station_id, at)
    if context is None:
        raise HTTPException(status_code=404, detail=f"Unknown station id {request.station_id}.")

    return EvidenceAggregator().evaluate(context)


@router.get(
    "/evaluate",
    response_model=EvidenceReport,
    summary="Evidence report for a station and time (GET form)",
)
async def evidence_evaluate_get(
    session: DbSessionDep,
    station_id: int = Query(description="Station id."),
    at: dt.datetime = Query(description="Instant to explain, ISO 8601."),
) -> EvidenceReport:
    """GET form of `/evidence/evaluate`, for links and quick inspection."""
    return await evidence_evaluate(EvaluateRequest(station_id=station_id, at=at), session)
