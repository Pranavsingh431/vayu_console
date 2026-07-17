"""The evidence module contract.

Composability is the design goal. Each module:

* receives a plain `EvidenceContext` — never a database session, so it is testable
  with no I/O and replaceable without touching the aggregator;
* returns an `EvidenceResult` and never raises for missing data;
* declares its own identification status and historical validation.

The aggregator knows only this interface. Adding a construction or dust module in
a later phase means implementing `EvidenceModule` and registering it — nothing in
the aggregator changes.
"""

from __future__ import annotations

import abc
import datetime as dt
from dataclasses import dataclass, field
from typing import Any

from app.evidence.schemas.evidence import (
    STRENGTH_EXPLANATION,
    STRENGTH_STARS,
    EvidenceQuality,
    EvidenceResult,
    EvidenceStrength,
    HistoricalValidation,
    Hypothesis,
    Identification,
    Observation,
)


@dataclass(frozen=True, slots=True)
class FireObservation:
    """One fire detection, already resolved relative to the station."""

    latitude: float
    longitude: float
    acquired_at: dt.datetime
    frp_mw: float | None
    confidence: str | None
    distance_km: float
    # Degrees between the station's upwind direction and the fire's bearing. 0
    # means the fire lies exactly upwind; 180 means exactly downwind.
    bearing_offset_deg: float | None
    source: str


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    """Everything a module may look at, for one station at one instant.

    A plain dataclass rather than a session: modules must be unit-testable without
    a database, and the aggregator owns all I/O. Every field is optional because
    absence is the normal case — a station without SO2, a satellite with no pass.
    """

    station_name: str
    evaluated_at: dt.datetime
    station_id: int | None = None
    latitude: float | None = None
    longitude: float | None = None

    # Pollutant concentrations at this station-hour, µg/m³ (CO in µg/m³ as stored).
    pollutants: dict[str, float] = field(default_factory=dict)
    # The preceding hours of this station's PM2.5/NO2, oldest first, for diurnal shape.
    recent_hours: dict[str, list[tuple[dt.datetime, float]]] = field(default_factory=dict)

    # Meteorology at the nearest grid point.
    wind_speed_ms: float | None = None
    wind_direction_deg: float | None = None
    boundary_layer_height_m: float | None = None
    temperature_c: float | None = None
    relative_humidity_pct: float | None = None

    fires: list[FireObservation] = field(default_factory=list)
    # True when a FIRMS query ran and legitimately returned nothing. Distinguishes
    # "no fires" (evidence against biomass) from "we did not look" (insufficient).
    fires_queried: bool = False

    # Static spatial context. Absent until the OSM/wards work lands.
    road_density_km_per_km2: float | None = None
    industrial_proximity_km: float | None = None
    power_plant_proximity_km: float | None = None

    def has(self, *pollutants: str) -> bool:
        """Whether every named pollutant is present and non-negative.

        Negatives are excluded here rather than downstream: the archive carries
        -999 sentinels and CO values near -476300, and a module must never reason
        over a sentinel. See scientific-limitations.md.
        """
        return all((value := self.pollutants.get(p)) is not None and value >= 0 for p in pollutants)

    def ist_hour(self) -> int:
        """Hour of day in IST.

        Diurnal reasoning must be local: Delhi's rush hours and Diwali's firework
        peak are IST phenomena, and reading UTC shifts them by 5.5 hours.
        """
        ist = dt.timezone(dt.timedelta(hours=5, minutes=30))
        return self.evaluated_at.astimezone(ist).hour


class EvidenceModule(abc.ABC):
    """One hypothesis, evaluated independently of the others."""

    #: Module name, used as the registry key and in reports.
    name: str
    #: The hypothesis this module argues about.
    hypothesis: Hypothesis
    #: How well the data identifies this hypothesis at all (inference.md §5.6).
    identification: Identification

    @abc.abstractmethod
    def evaluate(self, context: EvidenceContext) -> EvidenceResult:
        """Judge the hypothesis from the context.

        Must never raise for missing or malformed data — return
        `insufficient(...)` instead. A module that throws takes the whole report
        down with it, and an officer loses the evidence that *was* available.
        """

    # -- helpers shared by every module ------------------------------------

    def _result(
        self,
        strength: EvidenceStrength,
        quality: EvidenceQuality,
        *,
        supporting: list[Observation] | None = None,
        contradicting: list[Observation] | None = None,
        assumptions: list[str] | None = None,
        limitations: list[str] | None = None,
        historical_validation: list[HistoricalValidation] | None = None,
        references: list[str] | None = None,
        likelihood_ratio: float | None = None,
    ) -> EvidenceResult:
        return EvidenceResult(
            name=self.name,
            hypothesis=self.hypothesis,
            status=strength,
            strength=strength,
            evidence_quality=quality,
            identification=self.identification,
            stars=STRENGTH_STARS[strength],
            explanation=STRENGTH_EXPLANATION[strength],
            likelihood_ratio=likelihood_ratio,
            supporting_observations=supporting or [],
            contradicting_observations=contradicting or [],
            assumptions=assumptions or [],
            limitations=limitations or [],
            historical_validation=historical_validation or [],
            references=references or [],
        )

    def insufficient(self, reason: str, **kwargs: Any) -> EvidenceResult:
        """Report that the hypothesis could not be judged.

        A first-class outcome. "We cannot see" is information an officer can act
        on; a fabricated weak score is not.
        """
        return self._result(
            EvidenceStrength.INSUFFICIENT_EVIDENCE,
            EvidenceQuality.NO_DATA,
            limitations=[reason],
            **kwargs,
        )
