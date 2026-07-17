"""Tests for the evidence modules.

The important cases are the absences. A module that invents a score from missing
data is the failure mode this whole engine exists to prevent, so most of what is
pinned here is what happens when we cannot see.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app.evidence.base import EvidenceContext, FireObservation
from app.evidence.biomass import BiomassEvidenceModule, wind_weighted_influence
from app.evidence.industrial import IndustrialEvidenceModule
from app.evidence.schemas import (
    EvidenceQuality,
    EvidenceStrength,
    Identification,
    ValidationStatus,
)
from app.evidence.traffic import TrafficEvidenceModule

# 27 Oct 2019 18:00 UTC == 23:30 IST — Diwali's firework peak, deliberately
# outside any commute window.
DIWALI_PEAK = dt.datetime(2019, 10, 27, 18, 0, tzinfo=dt.UTC)
# 03:30 UTC == 09:00 IST — inside the morning commute peak.
MORNING_RUSH = dt.datetime(2019, 10, 24, 3, 30, tzinfo=dt.UTC)


def ctx(**kwargs: object) -> EvidenceContext:
    base: dict[str, object] = {"station_name": "Test Station", "evaluated_at": DIWALI_PEAK}
    base.update(kwargs)
    return EvidenceContext(**base)  # type: ignore[arg-type]


def fire(
    distance_km: float = 200.0,
    bearing_offset_deg: float | None = 10.0,
    frp: float | None = 40.0,
    age_h: float = 6.0,
) -> FireObservation:
    return FireObservation(
        latitude=30.2,
        longitude=76.4,
        acquired_at=DIWALI_PEAK - dt.timedelta(hours=age_h),
        frp_mw=frp,
        confidence="h",
        distance_km=distance_km,
        bearing_offset_deg=bearing_offset_deg,
        source="firms_viirs_snpp_sp",
    )


# ---------------------------------------------------------------- biomass ----


class TestBiomass:
    def test_insufficient_when_firms_not_queried(self) -> None:
        """Not querying FIRMS is not evidence that no fires burned."""
        result = BiomassEvidenceModule().evaluate(ctx(fires_queried=False))

        assert result.strength == EvidenceStrength.INSUFFICIENT_EVIDENCE
        assert result.evidence_quality == EvidenceQuality.NO_DATA
        assert result.likelihood_ratio is None
        assert any("not evidence against fire" in limit for limit in result.limitations)

    def test_no_fires_found_is_evidence_against_not_insufficient(self) -> None:
        """FIRMS looking and finding nothing is a real observation."""
        result = BiomassEvidenceModule().evaluate(
            ctx(
                fires_queried=True,
                fires=[],
                wind_direction_deg=315.0,
                boundary_layer_height_m=800.0,
            )
        )

        assert result.strength != EvidenceStrength.INSUFFICIENT_EVIDENCE
        assert result.strength == EvidenceStrength.VERY_WEAK
        assert any("No fire detections" in o.label for o in result.contradicting_observations)

    def test_many_upwind_fires_raise_strength(self) -> None:
        fires = [fire(distance_km=150.0, frp=80.0) for _ in range(40)]
        result = BiomassEvidenceModule().evaluate(
            ctx(
                fires_queried=True,
                fires=fires,
                wind_direction_deg=315.0,
                boundary_layer_height_m=210.0,
            )
        )

        assert result.likelihood_ratio is not None
        assert result.likelihood_ratio > 1.0
        assert result.supporting_observations

    def test_downwind_fires_contribute_nothing(self) -> None:
        """Smoke does not travel against the wind."""
        result = BiomassEvidenceModule().evaluate(
            ctx(
                fires_queried=True,
                fires=[fire(bearing_offset_deg=170.0) for _ in range(50)],
                wind_direction_deg=315.0,
                boundary_layer_height_m=210.0,
            )
        )

        assert result.strength == EvidenceStrength.VERY_WEAK
        assert any("none upwind" in o.label for o in result.contradicting_observations)

    def test_missing_wind_degrades_quality_not_strength(self) -> None:
        """Strong-looking evidence on poor data must stay visible as poor data."""
        result = BiomassEvidenceModule().evaluate(
            ctx(fires_queried=True, fires=[fire() for _ in range(20)], wind_direction_deg=None)
        )

        assert result.evidence_quality == EvidenceQuality.POOR
        assert any(
            "Wind direction unavailable" in o.label for o in result.contradicting_observations
        )

    def test_identification_is_strong(self) -> None:
        """Biomass is the one hypothesis with a signal exogenous to the monitor."""
        assert BiomassEvidenceModule().identification == Identification.STRONG

    def test_module_never_claims_a_contribution(self) -> None:
        result = BiomassEvidenceModule().evaluate(
            ctx(fires_queried=True, fires=[fire()], wind_direction_deg=315.0)
        )
        blob = result.model_dump_json().lower()

        assert "%" not in blob
        assert "contribution" not in blob or "not a measure of fire contribution" in blob


class TestWindWeightedInfluence:
    def test_distance_decay_halves_at_the_half_distance(self) -> None:
        near = wind_weighted_influence(fire(distance_km=0.0, bearing_offset_deg=0.0), None)
        far = wind_weighted_influence(fire(distance_km=150.0, bearing_offset_deg=0.0), None)

        assert far == pytest.approx(near * 0.5, rel=1e-6)

    def test_beyond_max_range_is_zero(self) -> None:
        assert wind_weighted_influence(fire(distance_km=500.0), None) == 0.0

    def test_downwind_is_zero(self) -> None:
        assert wind_weighted_influence(fire(bearing_offset_deg=90.0), None) == 0.0

    def test_unknown_bearing_is_discounted_not_assumed_aligned(self) -> None:
        """Ignorance must not manufacture evidence."""
        aligned = wind_weighted_influence(fire(bearing_offset_deg=0.0), None)
        unknown = wind_weighted_influence(fire(bearing_offset_deg=None), None)

        assert 0 < unknown < aligned

    def test_missing_frp_does_not_discard_the_detection(self) -> None:
        """A fire with no FRP is still a fire."""
        assert wind_weighted_influence(fire(frp=None, bearing_offset_deg=0.0), None) > 0

    def test_low_boundary_layer_amplifies(self) -> None:
        high = wind_weighted_influence(fire(bearing_offset_deg=0.0), 1500.0)
        low = wind_weighted_influence(fire(bearing_offset_deg=0.0), 200.0)

        assert low > high


# ---------------------------------------------------------------- traffic ----


class TestTraffic:
    def test_insufficient_without_no2(self) -> None:
        result = TrafficEvidenceModule().evaluate(ctx(pollutants={"so2": 8.0}))

        assert result.strength == EvidenceStrength.INSUFFICIENT_EVIDENCE
        assert any("not evidence against traffic" in limit for limit in result.limitations)

    def test_no2_without_so2_is_very_weak_and_poor_quality(self) -> None:
        """Without SO2 there is nothing to separate traffic from point sources."""
        result = TrafficEvidenceModule().evaluate(ctx(pollutants={"no2": 80.0}))

        assert result.strength == EvidenceStrength.VERY_WEAK
        assert result.evidence_quality == EvidenceQuality.POOR
        assert any("SO2 unavailable" in o.label for o in result.contradicting_observations)

    def test_off_peak_hour_is_reported_as_contradicting(self) -> None:
        """A 23:30 IST spike is not a commute profile, and the module must say so."""
        result = TrafficEvidenceModule().evaluate(
            ctx(pollutants={"no2": 64.0, "so2": 11.0}, evaluated_at=DIWALI_PEAK)
        )

        assert any("outside commute peaks" in o.label for o in result.contradicting_observations)

    def test_rush_hour_with_high_ratio_supports(self) -> None:
        result = TrafficEvidenceModule().evaluate(
            ctx(pollutants={"no2": 90.0, "so2": 6.0}, evaluated_at=MORNING_RUSH)
        )

        assert result.strength in {EvidenceStrength.WEAK, EvidenceStrength.MODERATE}
        assert result.likelihood_ratio is not None

    def test_lockdown_like_ratio_is_evidence_against(self) -> None:
        """A ratio in the suppressed regime argues against traffic dominance."""
        result = TrafficEvidenceModule().evaluate(
            ctx(pollutants={"no2": 10.0, "so2": 9.0}, evaluated_at=MORNING_RUSH)
        )

        assert result.likelihood_ratio is not None
        assert result.likelihood_ratio < 1.0
        assert any("NO2/SO2" in o.label for o in result.contradicting_observations)

    def test_strength_is_capped_at_moderate(self) -> None:
        """The COVID calibration measured LR 1.93 — weak. No reading may claim more."""
        module = TrafficEvidenceModule()
        for no2 in (50.0, 500.0, 5000.0):
            result = module.evaluate(
                ctx(pollutants={"no2": no2, "so2": 1.0}, evaluated_at=MORNING_RUSH)
            )
            assert result.strength in {
                EvidenceStrength.VERY_WEAK,
                EvidenceStrength.WEAK,
                EvidenceStrength.MODERATE,
            }

    def test_covid_validation_is_accepted_and_states_the_failure_condition(self) -> None:
        result = TrafficEvidenceModule().evaluate(ctx(pollutants={"no2": 40.0, "so2": 8.0}))
        covid = next(v for v in result.historical_validation if "COVID" in v.experiment)

        assert covid.status == ValidationStatus.ACCEPTED
        assert "would have been rejected" in covid.detail.lower()
        assert covid.likelihood_ratio == pytest.approx(2.11, abs=0.02)

    def test_odd_even_validation_is_pending(self) -> None:
        result = TrafficEvidenceModule().evaluate(ctx(pollutants={"no2": 40.0}))
        odd_even = next(v for v in result.historical_validation if "Odd-Even" in v.experiment)

        assert odd_even.status == ValidationStatus.PENDING

    def test_identification_is_weak(self) -> None:
        assert TrafficEvidenceModule().identification == Identification.WEAK


# ------------------------------------------------------------- industrial ----


class TestIndustrial:
    def test_missing_so2_is_insufficient_and_says_absence_is_not_absence(self) -> None:
        """The trap: no sensor must never read as 'industry is not a problem here'."""
        result = IndustrialEvidenceModule().evaluate(ctx(pollutants={"no2": 40.0}))

        assert result.strength == EvidenceStrength.INSUFFICIENT_EVIDENCE
        assert any("cannot see" in limit for limit in result.limitations)
        assert any("NOT evidence that industry is absent" in limit for limit in result.limitations)

    def test_never_reports_a_likelihood_ratio(self) -> None:
        """No natural experiment isolates industry, so there is no LR to report."""
        result = IndustrialEvidenceModule().evaluate(ctx(pollutants={"so2": 90.0}))

        assert result.likelihood_ratio is None

    def test_elevated_so2_is_at_most_weak(self) -> None:
        result = IndustrialEvidenceModule().evaluate(ctx(pollutants={"so2": 500.0}))

        assert result.strength == EvidenceStrength.WEAK
        assert result.evidence_quality == EvidenceQuality.POOR

    def test_low_so2_is_evidence_against(self) -> None:
        result = IndustrialEvidenceModule().evaluate(ctx(pollutants={"so2": 3.0}))

        assert result.strength == EvidenceStrength.VERY_WEAK
        assert result.contradicting_observations

    def test_covid_validation_is_uncertain_not_accepted(self) -> None:
        """Lockdown stopped industry alongside traffic — it cannot isolate this."""
        result = IndustrialEvidenceModule().evaluate(ctx(pollutants={"so2": 9.0}))
        covid = next(v for v in result.historical_validation if "COVID" in v.experiment)

        assert covid.status == ValidationStatus.UNCERTAIN

    def test_identification_is_very_weak(self) -> None:
        assert IndustrialEvidenceModule().identification == Identification.VERY_WEAK
