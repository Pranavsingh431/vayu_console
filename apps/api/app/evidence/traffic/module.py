"""Traffic evidence.

Weakly identified, and the module says so on every response.

Traffic has no signal exogenous to the monitor: unlike fire, there is no satellite
watching Delhi's cars. Its only signature is in the same chemistry we would reason
from, which is why Phase 2 rejected a supervised classifier here
(docs/research/inference.md §3).

What rescues the module from being a heuristic is the COVID lockdown. Traffic went
to ~0 by government order, which makes `P(NO2 | vehicles ≈ 0)` directly observable
rather than assumed (§5.5). Measured over Delhi, 1-23 Mar 2020 vs 25 Mar - 30 Apr 2020:

    no2    32.7 -> 14.9   -54.4%
    so2    11.6 -> 11.2    -3.7%

NO2 halved while SO2 held flat. Power generation was essential and kept running, so
this is a *differential* intervention — and the test could have failed. It did not,
so the module is ACCEPTED.

But rated honestly: the NO2/SO2 ratio moved 2.82 -> 1.34, a likelihood ratio of
2.11, which is Kass & Raftery "weak". NO2 responds strongly to traffic; the ratio
is only a weak discriminator against point sources. And lockdown also halted
construction and industry, so the LR is an **upper bound** on the traffic-only
effect.
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
    strength_from_likelihood_ratio,
)

# --- Calibration constants, measured not chosen -----------------------------
#
# From scripts/stress_test.py against the COVID lockdown. Station-hour medians
# over Delhi, sentinels excluded. Update these only by re-running the test.
#
# Full ingest: 47 stations, 901,160 rows. A preliminary 3-station run gave
# -51.5% / -6.6% and LR 1.93; the finding replicated at 15x the sample.

COVID_NO2_NORMAL = 32.7
COVID_NO2_SUPPRESSED = 14.9
COVID_SO2_NORMAL = 11.6
COVID_SO2_SUPPRESSED = 11.2

#: NO2/SO2 under normal traffic vs suppressed traffic.
RATIO_NORMAL = COVID_NO2_NORMAL / COVID_SO2_NORMAL  # 2.82
RATIO_SUPPRESSED = COVID_NO2_SUPPRESSED / COVID_SO2_SUPPRESSED  # 1.34

#: The measured likelihood ratio for the traffic hypothesis. Weak, and honest.
COVID_LIKELIHOOD_RATIO = RATIO_NORMAL / RATIO_SUPPRESSED  # ~2.11

# Delhi's twin commute peaks, IST. Morning is the sharper of the two.
MORNING_PEAK = (7, 11)
EVENING_PEAK = (17, 21)


def _in_peak(hour: int) -> bool:
    return MORNING_PEAK[0] <= hour <= MORNING_PEAK[1] or EVENING_PEAK[0] <= hour <= EVENING_PEAK[1]


class TrafficEvidenceModule(EvidenceModule):
    """Evidence that vehicle emissions are influencing this station."""

    name = "traffic"
    hypothesis = Hypothesis.TRAFFIC
    identification = Identification.WEAK

    _ASSUMPTIONS: ClassVar[list[str]] = [
        "NO2 is treated as a traffic-responsive species. Supported by the COVID "
        "lockdown (NO2 -54.4% while SO2 held at -3.7%), but lockdown also stopped "
        "construction and industry, so the association is an upper bound.",
        "SO2 is treated as dominated by point sources (power, industry) rather than "
        "traffic. Consistent with SO2 holding flat while traffic stopped.",
        "The NO2/SO2 ratio is assumed to separate distributed from point-source "
        "combustion. Measured LR is 2.11 — weak. It leans, it does not decide.",
        "Delhi's commute peaks are assumed at 07-11 and 17-21 IST.",
    ]
    _LIMITATIONS: ClassVar[list[str]] = [
        "Traffic has no signal exogenous to the monitor. All evidence here comes "
        "from the same chemistry being explained, so it can never be as strong as "
        "biomass evidence.",
        "The COVID calibration cannot separate traffic from construction or "
        "industry: all three stopped together.",
        "NO2 has a short atmospheric lifetime and is also produced by any "
        "high-temperature combustion, including generators and industry.",
        "Road density is not yet ingested, so the spatial term is unavailable.",
    ]
    _REFERENCES: ClassVar[list[str]] = [
        "Vayu Console stress test: COVID lockdown 2020, scripts/stress_test.py.",
        "Kass, R. & Raftery, A. (1995). Bayes Factors. JASA 90(430).",
    ]

    def _validation(self) -> list[HistoricalValidation]:
        return [
            HistoricalValidation(
                experiment="COVID lockdown 2020",
                status=ValidationStatus.ACCEPTED,
                detail=(
                    "Would have been rejected if NO2 had not fallen materially when "
                    "traffic went to ~0, or if SO2 had fallen with it. Measured over "
                    "47 stations / 901,160 rows: NO2 -54.4%, SO2 -3.7%; NO2/SO2 "
                    "2.82 -> 1.34. The differential the hypothesis requires."
                ),
                likelihood_ratio=COVID_LIKELIHOOD_RATIO,
            ),
            HistoricalValidation(
                experiment="Odd-Even II, April 2016",
                status=ValidationStatus.PENDING,
                detail=(
                    "The only unconfounded vehicle window: no stubble, no winter "
                    "inversion. Weak treatment (2-wheelers and CNG exempt) on 11 "
                    "stations. Not yet ingested."
                ),
            ),
        ]

    def evaluate(self, context: EvidenceContext) -> EvidenceResult:
        # NO2 is the load-bearing observation. Without it there is nothing to say.
        if not context.has("no2"):
            return self.insufficient(
                "NO2 is unavailable at this station-hour. Traffic evidence rests on "
                "NO2; without it the hypothesis cannot be judged. This is not "
                "evidence against traffic.",
                assumptions=self._ASSUMPTIONS,
                references=self._REFERENCES,
                historical_validation=self._validation(),
            )

        supporting: list[Observation] = []
        contradicting: list[Observation] = []
        no2 = context.pollutants["no2"]

        supporting.append(
            Observation(
                label="NO2",
                value=round(no2, 1),
                unit="µg/m³",
                source="openaq_s3",
                observed_at=context.evaluated_at,
            )
        )

        # --- Ratio evidence, only where SO2 exists ---------------------------
        lr: float | None = None
        if context.has("so2") and context.pollutants["so2"] > 0:
            so2 = context.pollutants["so2"]
            ratio = no2 / so2
            obs = Observation(
                label="NO2/SO2 ratio",
                value=round(ratio, 2),
                source="openaq_s3",
                observed_at=context.evaluated_at,
            )
            if ratio >= RATIO_NORMAL:
                supporting.append(obs)
                lr = COVID_LIKELIHOOD_RATIO
            elif ratio <= RATIO_SUPPRESSED:
                # Looks like the lockdown regime: distributed combustion is not
                # dominating. That is evidence against, and must be reported.
                contradicting.append(obs)
                lr = 1.0 / COVID_LIKELIHOOD_RATIO
            else:
                supporting.append(obs)
                lr = 1.0
        else:
            contradicting.append(
                Observation(
                    label="SO2 unavailable — cannot separate traffic from point sources",
                    source="openaq_s3",
                )
            )

        # --- Diurnal evidence -------------------------------------------------
        hour = context.ist_hour()
        peak_obs = Observation(
            label=f"Hour {hour:02d}:00 IST",
            value=hour,
            source="derived",
            observed_at=context.evaluated_at,
        )
        if _in_peak(hour):
            supporting.append(peak_obs)
        else:
            # Explicitly reported. A 23:30 IST spike is NOT a commute profile, and
            # a module that only reports agreeing facts is advocacy, not evidence.
            contradicting.append(
                Observation(
                    label=f"Hour {hour:02d}:00 IST is outside commute peaks (07-11, 17-21)",
                    value=hour,
                    source="derived",
                    observed_at=context.evaluated_at,
                )
            )

        if context.road_density_km_per_km2 is not None:
            supporting.append(
                Observation(
                    label="Road density",
                    value=round(context.road_density_km_per_km2, 2),
                    unit="km/km²",
                    source="osm",
                )
            )

        strength = self._strength(lr, hour)
        quality = self._quality(context)

        return self._result(
            strength,
            quality,
            supporting=supporting,
            contradicting=contradicting,
            assumptions=self._ASSUMPTIONS,
            limitations=self._LIMITATIONS,
            historical_validation=self._validation(),
            references=self._REFERENCES,
            likelihood_ratio=lr,
        )

    def _strength(self, lr: float | None, hour: int) -> EvidenceStrength:
        """Combine ratio and diurnal evidence.

        Capped at MODERATE regardless of what the observations show. The COVID
        calibration measured LR 2.11 — weak — so this module has no basis to ever
        claim strong evidence. The cap is the measurement, enforced in code.
        """
        if lr is None:
            # NO2 alone, no SO2: the weakest defensible statement.
            return EvidenceStrength.VERY_WEAK

        base = strength_from_likelihood_ratio(lr)
        if _in_peak(hour) and lr > 1.0:
            order = [
                EvidenceStrength.VERY_WEAK,
                EvidenceStrength.WEAK,
                EvidenceStrength.MODERATE,
            ]
            idx = order.index(base) if base in order else 0
            base = order[min(idx + 1, len(order) - 1)]

        ceiling = EvidenceStrength.MODERATE
        ranks = {
            EvidenceStrength.VERY_WEAK: 0,
            EvidenceStrength.WEAK: 1,
            EvidenceStrength.MODERATE: 2,
            EvidenceStrength.STRONG: 3,
            EvidenceStrength.VERY_STRONG: 4,
        }
        return base if ranks.get(base, 0) <= ranks[ceiling] else ceiling

    @staticmethod
    def _quality(context: EvidenceContext) -> EvidenceQuality:
        if not context.has("no2"):
            return EvidenceQuality.NO_DATA
        if not context.has("so2"):
            # NO2 present but nothing to contrast it against.
            return EvidenceQuality.POOR
        if context.road_density_km_per_km2 is None:
            return EvidenceQuality.FAIR
        return EvidenceQuality.GOOD
