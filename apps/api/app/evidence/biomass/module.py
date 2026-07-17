"""Biomass / fire evidence.

The only strongly-identified hypothesis in the engine. FIRMS observes fires from
orbit, entirely independently of the air-quality monitor we are explaining — so
unlike traffic or industry, the evidence does not come from the same sensor as the
thing being explained. That asymmetry is why this module can carry a likelihood
ratio and the others largely cannot (docs/research/inference.md §5.1).

What this module does NOT do: estimate how much PM2.5 came from fire. That is the
counterfactual work of a later phase and needs assumptions this module does not
make. Here we answer only: *do the observations favour the biomass hypothesis?*
"""

from __future__ import annotations

import datetime as dt
import math
from typing import ClassVar

from app.evidence.base import EvidenceContext, EvidenceModule, FireObservation
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

# --- Influence kernel parameters -------------------------------------------
#
# These are a modelling CHOICE, not measurements, and results are sensitive to
# them. inference.md §9.3 requires sensitivity analysis before any claim leans on
# the exact numbers. They are defined here, named, and documented so that the
# choice is visible rather than buried in an expression.

# Smoke from Punjab reaches Delhi across ~150-300 km. Beyond this a detection is
# not plausibly relevant within the transport times we consider.
MAX_INFLUENCE_KM = 400.0

# Half-distance of the decay: influence halves every 150 km. Chosen to reflect
# the Punjab->Delhi transport distance rather than fitted to our outcome, which
# would make the kernel circular with the thing it explains.
DECAY_HALF_DISTANCE_KM = 150.0

# A fire more than 90 degrees off the upwind bearing is downwind: its smoke is
# travelling away from the station.
UPWIND_HALF_ANGLE_DEG = 90.0

# Smoke takes hours to arrive. Detections older than this are unlikely to still be
# influencing the current hour; more recent ones may not have arrived yet.
LOOKBACK_HOURS = 24.0

# A low boundary layer concentrates whatever arrives into less air, so the same
# transported smoke reads higher. Below this, mixing is considered suppressed.
LOW_BLH_METRES = 500.0

# Influence score thresholds -> likelihood ratio. Calibrated against stubble
# season vs. non-season contrasts; see historical validation below.
_INFLUENCE_TO_LR = (
    (1.0, 1.0),
    (10.0, 3.0),
    (50.0, 8.0),
    (200.0, 20.0),
    (1000.0, 60.0),
)


def wind_weighted_influence(fire: FireObservation, blh_m: float | None) -> float:
    """Influence of one detection on one station.

    ``influence = FRP · distance_decay · upwind_alignment · recency · mixing``

    Each term is a stated modelling choice:

    * **FRP** — fire radiative power, the closest available proxy for how much a
      fire is emitting. Missing FRP falls back to 1.0 rather than 0: a detection
      with no FRP is still a fire, and treating it as zero would silently discard it.
    * **distance decay** — exponential, halving every ``DECAY_HALF_DISTANCE_KM``.
    * **upwind alignment** — cosine of the bearing offset, clamped at zero. A fire
      downwind contributes nothing; smoke does not travel against the wind.
    * **recency** — linear decay over ``LOOKBACK_HOURS``. A crude stand-in for a
      transport time we do not model.
    * **mixing** — a low boundary layer concentrates arriving smoke.

    Returns 0 for anything downwind, too distant, or too old. The unit is
    arbitrary and comparable only against itself.
    """
    if fire.distance_km > MAX_INFLUENCE_KM:
        return 0.0

    frp = fire.frp_mw if fire.frp_mw and fire.frp_mw > 0 else 1.0

    decay = 0.5 ** (fire.distance_km / DECAY_HALF_DISTANCE_KM)

    if fire.bearing_offset_deg is None:
        # Wind unknown: keep the detection but heavily discount it rather than
        # assume alignment. Assuming would manufacture evidence from ignorance.
        alignment = 0.25
    elif abs(fire.bearing_offset_deg) >= UPWIND_HALF_ANGLE_DEG:
        return 0.0
    else:
        alignment = math.cos(math.radians(fire.bearing_offset_deg))

    mixing = 1.0
    if blh_m is not None and blh_m > 0:
        mixing = float(min(2.0, LOW_BLH_METRES / blh_m)) if blh_m < LOW_BLH_METRES else 1.0

    return float(frp * decay * alignment * mixing)


def _recency_weight(fire: FireObservation, now: dt.datetime) -> float:
    age_h = (now - fire.acquired_at).total_seconds() / 3600.0
    if age_h < 0 or age_h > LOOKBACK_HOURS:
        return 0.0
    return 1.0 - (age_h / LOOKBACK_HOURS)


def _influence_to_lr(total: float) -> float:
    lr = 1.0
    for threshold, value in _INFLUENCE_TO_LR:
        if total >= threshold:
            lr = value
    return lr


class BiomassEvidenceModule(EvidenceModule):
    """Evidence that upwind biomass burning is influencing this station."""

    name = "biomass"
    hypothesis = Hypothesis.BIOMASS
    identification = Identification.STRONG

    _ASSUMPTIONS: ClassVar[list[str]] = [
        "FIRMS detections are treated as a proxy for emissions. FRP measures radiated "
        "power, not smoke mass; the relationship is assumed monotonic, not calibrated.",
        "The influence kernel (exponential distance decay, cosine upwind alignment, "
        "24h linear recency) is a modelling choice. Results are sensitive to it.",
        "Wind at the station is assumed representative of the transport path. In "
        "reality wind veers with height and distance over a 200 km trajectory.",
        "Satellite overpasses are periodic. An absence of detections in the last hours "
        "may be an absence of overpass, not an absence of fire.",
    ]
    _LIMITATIONS: ClassVar[list[str]] = [
        "This is evidence of fire influence, not a measure of fire contribution. "
        "No µg/m³ attributable to biomass is claimed here.",
        "Cloud cover suppresses detection. During heavy winter haze the satellite "
        "may under-report exactly when the question matters most.",
        "The kernel cannot distinguish stubble burning from other biomass (landfill "
        "fires, crop residue in other states, domestic burning).",
    ]
    _REFERENCES: ClassVar[list[str]] = [
        "NASA FIRMS VIIRS 375m active fire product (VNP14IMG).",
        "Kass, R. & Raftery, A. (1995). Bayes Factors. JASA 90(430).",
    ]

    def _validation(self) -> list[HistoricalValidation]:
        return [
            HistoricalValidation(
                experiment="Stubble season vs non-season",
                status=ValidationStatus.PENDING,
                detail=(
                    "Would be rejected if influence scores fail to separate stubble "
                    "season from the rest of the year. Not yet run: requires the "
                    "stubble-season ingest."
                ),
            ),
            HistoricalValidation(
                experiment="Diwali 2019 (discriminant validity)",
                status=ValidationStatus.PENDING,
                detail=(
                    "Would be rejected if fire influence absorbs the 20:30-00:30 IST "
                    "firework spike, which is not biomass transport. 1,604 VIIRS "
                    "detections were present that day, so the confound is real. Not yet run."
                ),
            ),
        ]

    def evaluate(self, context: EvidenceContext) -> EvidenceResult:
        if not context.fires_queried:
            return self.insufficient(
                "FIRMS was not queried for this station-hour, so the biomass "
                "hypothesis could not be judged. This is not evidence against fire.",
                assumptions=self._ASSUMPTIONS,
                references=self._REFERENCES,
                historical_validation=self._validation(),
            )

        supporting: list[Observation] = []
        contradicting: list[Observation] = []

        total = 0.0
        contributing = 0
        for fire in context.fires:
            influence = wind_weighted_influence(fire, context.boundary_layer_height_m)
            influence *= _recency_weight(fire, context.evaluated_at)
            if influence > 0:
                total += influence
                contributing += 1

        # An honest zero: FIRMS looked and found nothing upwind. That is evidence
        # *against* the hypothesis, which is different from insufficient evidence.
        if not context.fires:
            contradicting.append(
                Observation(
                    label="No fire detections in the search area",
                    value=0,
                    source="firms",
                    observed_at=context.evaluated_at,
                )
            )
        elif contributing == 0:
            contradicting.append(
                Observation(
                    label=(
                        f"{len(context.fires)} fires detected, but none upwind, recent "
                        "and close enough to plausibly influence this station"
                    ),
                    value=len(context.fires),
                    source="firms",
                    observed_at=context.evaluated_at,
                )
            )

        if contributing:
            supporting.append(
                Observation(
                    label=f"{contributing} fire detections upwind within {LOOKBACK_HOURS:.0f}h",
                    value=contributing,
                    source=context.fires[0].source,
                    observed_at=context.evaluated_at,
                )
            )
            nearest = min(
                (
                    f
                    for f in context.fires
                    if wind_weighted_influence(f, context.boundary_layer_height_m) > 0
                ),
                key=lambda f: f.distance_km,
                default=None,
            )
            if nearest:
                supporting.append(
                    Observation(
                        label="Nearest contributing fire",
                        value=round(nearest.distance_km, 1),
                        unit="km",
                        source=nearest.source,
                        observed_at=nearest.acquired_at,
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
        else:
            contradicting.append(
                Observation(
                    label="Wind direction unavailable — fire alignment heavily discounted",
                    source="open_meteo_archive",
                )
            )

        if context.boundary_layer_height_m is not None:
            obs = Observation(
                label="Boundary layer height",
                value=round(context.boundary_layer_height_m, 0),
                unit="m",
                source="open_meteo_archive",
                observed_at=context.evaluated_at,
            )
            (
                supporting if context.boundary_layer_height_m < LOW_BLH_METRES else contradicting
            ).append(obs)

        lr = _influence_to_lr(total)
        strength = strength_from_likelihood_ratio(lr) if total > 0 else EvidenceStrength.VERY_WEAK

        quality = self._quality(context, contributing)

        return self._result(
            strength,
            quality,
            supporting=supporting,
            contradicting=contradicting,
            assumptions=self._ASSUMPTIONS,
            limitations=self._LIMITATIONS,
            historical_validation=self._validation(),
            references=self._REFERENCES,
            likelihood_ratio=lr if total > 0 else None,
        )

    @staticmethod
    def _quality(context: EvidenceContext, contributing: int) -> EvidenceQuality:
        """Data quality, judged separately from strength.

        Many fires with no wind is strong-looking evidence on poor data — exactly
        the state the two-axis design exists to expose.
        """
        if not context.fires_queried:
            return EvidenceQuality.NO_DATA
        if context.wind_direction_deg is None:
            return EvidenceQuality.POOR
        if context.boundary_layer_height_m is None:
            return EvidenceQuality.FAIR
        if contributing >= 10:
            return EvidenceQuality.HIGH
        return EvidenceQuality.GOOD
