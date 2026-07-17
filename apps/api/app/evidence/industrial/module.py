"""Industrial / power evidence.

The weakest module in the engine, and the most important one to get honest.

Phase 2 concluded this hypothesis is close to unidentified (inference.md §5.6):

* **No intervention isolates industry.** COVID stopped traffic, construction and
  much industry at once, so it cannot calibrate industry alone. Power generation
  stayed essential throughout, which is what made COVID useful for *traffic* — and
  useless for this.
* **SO2 is measured at 36 of 96 Delhi stations.** At the other 60 the module is
  structurally blind.
* **Industrial and power-plant proximity are not yet ingested.**

So this module mostly returns `INSUFFICIENT_EVIDENCE`, and that is the correct
behaviour rather than a gap to be filled with a plausible-looking number.

The trap it exists to avoid: at a station with no SO2 sensor, a naive engine shows
low industrial evidence, and an officer reads "industry is not a problem here."
**Absence of an instrument is not absence of a source.** Every insufficient result
says so explicitly.
"""

from __future__ import annotations

from typing import ClassVar

from app.evidence.base import EvidenceContext, EvidenceModule
from app.evidence.schemas.evidence import (
    EvidenceQuality,
    EvidenceResult,
    EvidenceStrength,
    HistoricalValidation,
    Hypothesis,
    Identification,
    Observation,
    ValidationStatus,
)

# Delhi's October SO2 median across reporting stations, from stored data. Used
# only to say "this reading is high/low for Delhi", never to infer a contribution.
SO2_DELHI_MEDIAN = 11.6

# A reading several times the city median is worth reporting as a signal. The
# multiplier is a reporting threshold, not a calibrated likelihood ratio — this
# module has no calibrating experiment and therefore no LR.
SO2_ELEVATED_MULTIPLE = 3.0


class IndustrialEvidenceModule(EvidenceModule):
    """Evidence that industrial or power emissions are influencing this station."""

    name = "industrial"
    hypothesis = Hypothesis.INDUSTRIAL
    identification = Identification.VERY_WEAK

    _ASSUMPTIONS: ClassVar[list[str]] = [
        "SO2 is treated as a marker for point-source combustion (coal power, "
        "industry). Supported indirectly: SO2 held flat (-6.6%) through the COVID "
        "lockdown while NO2 halved (-54.4%), consistent with essential power "
        "generation continuing while distributed sources stopped.",
        "No assumption is made about how much PM2.5 any industrial source "
        "contributes. No such estimate is possible from our data.",
    ]
    _LIMITATIONS: ClassVar[list[str]] = [
        "NO natural experiment isolates industry. COVID stopped traffic, "
        "construction and industry simultaneously, so it cannot calibrate this "
        "hypothesis. This module therefore reports NO likelihood ratio.",
        "SO2 is measured at only 36 of 96 Delhi stations. At the remainder this "
        "module is structurally blind.",
        "Industrial and power-plant proximity are not yet ingested, so the spatial "
        "term is unavailable.",
        "Absence of an SO2 sensor is not absence of industrial influence. A low or "
        "missing reading must never be read as 'industry is not a problem here'.",
    ]
    _REFERENCES: ClassVar[list[str]] = [
        "Vayu Console stress test: COVID lockdown 2020, scripts/stress_test.py.",
    ]

    def _validation(self) -> list[HistoricalValidation]:
        return [
            HistoricalValidation(
                experiment="COVID lockdown 2020",
                status=ValidationStatus.UNCERTAIN,
                detail=(
                    "SO2 held roughly flat (-3.7%) while NO2 halved, consistent with "
                    "power generation remaining essential. But lockdown halted "
                    "industry alongside traffic, so this cannot isolate the "
                    "hypothesis. Suggestive, not a validation."
                ),
            ),
            HistoricalValidation(
                experiment="Dedicated industrial intervention",
                status=ValidationStatus.PENDING,
                detail=(
                    "None exists in our natural experiment table. Without one, this "
                    "module cannot be calibrated and cannot carry a likelihood ratio."
                ),
            ),
        ]

    def evaluate(self, context: EvidenceContext) -> EvidenceResult:
        if not context.has("so2"):
            return self.insufficient(
                "SO2 is unavailable at this station-hour. SO2 is the only industrial "
                "marker we measure, and it is present at just 36 of 96 Delhi "
                "stations. This is NOT evidence that industry is absent — it means "
                "we cannot see.",
                assumptions=self._ASSUMPTIONS,
                references=self._REFERENCES,
                historical_validation=self._validation(),
            )

        so2 = context.pollutants["so2"]
        supporting: list[Observation] = []
        contradicting: list[Observation] = []

        so2_obs = Observation(
            label="SO2",
            value=round(so2, 1),
            unit="µg/m³",
            source="openaq_s3",
            observed_at=context.evaluated_at,
        )

        elevated = so2 >= SO2_DELHI_MEDIAN * SO2_ELEVATED_MULTIPLE
        (supporting if elevated else contradicting).append(so2_obs)

        if not elevated:
            contradicting.append(
                Observation(
                    label=(
                        f"SO2 {so2:.1f} µg/m³ is below {SO2_ELEVATED_MULTIPLE:g}x the Delhi "
                        f"median ({SO2_DELHI_MEDIAN} µg/m³)"
                    ),
                    value=round(so2, 1),
                    unit="µg/m³",
                    source="derived",
                    observed_at=context.evaluated_at,
                )
            )

        if context.wind_direction_deg is not None:
            supporting.append(
                Observation(
                    label="Wind direction (from)",
                    value=round(context.wind_direction_deg, 0),
                    unit="deg",
                    source="open_meteo_archive",
                    observed_at=context.evaluated_at,
                )
            )
        if context.industrial_proximity_km is not None:
            supporting.append(
                Observation(
                    label="Nearest industrial area",
                    value=round(context.industrial_proximity_km, 1),
                    unit="km",
                    source="osm",
                )
            )
        else:
            contradicting.append(
                Observation(
                    label="Industrial proximity not ingested — cannot check upwind sources",
                    source="osm",
                )
            )

        # Capped at WEAK by construction. With no calibrating experiment there is
        # no basis for a stronger claim, whatever SO2 reads. The cap is the
        # honesty, enforced in code rather than left to a caller's discretion.
        strength = EvidenceStrength.WEAK if elevated else EvidenceStrength.VERY_WEAK

        return self._result(
            strength,
            EvidenceQuality.POOR,  # SO2 alone, no proximity, no calibration.
            supporting=supporting,
            contradicting=contradicting,
            assumptions=self._ASSUMPTIONS,
            limitations=self._LIMITATIONS,
            historical_validation=self._validation(),
            references=self._REFERENCES,
            likelihood_ratio=None,  # Deliberately absent: no calibrating experiment.
        )
