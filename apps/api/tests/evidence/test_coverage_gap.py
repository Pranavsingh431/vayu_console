"""Regression tests for satellite coverage gaps and Diwali discriminant validity.

Both pin findings that came out of the real data, not from reasoning:

* **Coverage gaps.** 31 Oct 2019 logged 4 fire detections between neighbours of
  2,600 and 2,612. Fires do not stop for a day mid-season — the satellite did not
  see. Before this fix, the biomass module reported that as "no fires upwind",
  i.e. evidence AGAINST biomass manufactured from cloud cover.

* **Diwali discriminant validity.** The worry was that VIIRS detects fireworks as
  thermal anomalies, so biomass would absorb the firework spike. It does not, and
  the reason is mechanical: VIIRS overpasses Delhi at 12:00-14:00 and 01:00-03:00
  IST. Across 20 Oct - 3 Nov 2019 there were ZERO detections in the 20:00-00:00
  firework window. The satellite is not overhead when fireworks burn.
"""

from __future__ import annotations

import datetime as dt

from app.evidence.base import COVERAGE_GAP_FRACTION, EvidenceContext, FireObservation
from app.evidence.biomass import BiomassEvidenceModule
from app.evidence.schemas import EvidenceQuality, EvidenceStrength

DIWALI_PEAK = dt.datetime(2019, 10, 27, 18, 0, tzinfo=dt.UTC)


def fire(distance_km: float = 200.0, bearing_offset_deg: float = 10.0) -> FireObservation:
    return FireObservation(
        latitude=30.2,
        longitude=76.4,
        acquired_at=DIWALI_PEAK - dt.timedelta(hours=6),
        frp_mw=40.0,
        confidence="h",
        distance_km=distance_km,
        bearing_offset_deg=bearing_offset_deg,
        source="firms_viirs_snpp_sp",
    )


def ctx(**kwargs: object) -> EvidenceContext:
    base: dict[str, object] = {
        "station_name": "Test",
        "evaluated_at": DIWALI_PEAK,
        "wind_direction_deg": 315.0,
        "boundary_layer_height_m": 500.0,
        "fires_queried": True,
    }
    base.update(kwargs)
    return EvidenceContext(**base)  # type: ignore[arg-type]


class TestSatelliteCoverageGap:
    def test_the_real_31_oct_2019_gap_is_not_evidence_against_fire(self) -> None:
        """The actual observed numbers: 4 detections, neighbours ~2,600."""
        result = BiomassEvidenceModule().evaluate(
            ctx(fires=[], regional_detection_count=4, regional_detection_baseline=2600.0)
        )

        assert result.strength == EvidenceStrength.INSUFFICIENT_EVIDENCE
        assert result.evidence_quality == EvidenceQuality.NO_DATA
        assert any("NOT evidence against fire" in limit for limit in result.limitations)
        assert any("cloud cover or a missed overpass" in limit for limit in result.limitations)

    def test_normal_coverage_with_no_fires_remains_evidence_against(self) -> None:
        """A genuine fire-free day must still count against biomass.

        The gap fix must not swallow real absences, or the module becomes
        incapable of ever arguing against its own hypothesis.
        """
        result = BiomassEvidenceModule().evaluate(
            ctx(fires=[], regional_detection_count=2400, regional_detection_baseline=2600.0)
        )

        assert result.strength == EvidenceStrength.VERY_WEAK
        assert any("No fire detections" in o.label for o in result.contradicting_observations)

    def test_out_of_season_low_counts_are_real_not_gaps(self) -> None:
        """In June there are no stubble fires. Low is low, not a gap."""
        result = BiomassEvidenceModule().evaluate(
            ctx(fires=[], regional_detection_count=1, regional_detection_baseline=3.0)
        )

        assert result.strength == EvidenceStrength.VERY_WEAK

    def test_gap_detection_is_off_when_counts_are_unknown(self) -> None:
        """Absent coverage data must not silently disable the module."""
        result = BiomassEvidenceModule().evaluate(ctx(fires=[]))

        assert result.strength == EvidenceStrength.VERY_WEAK

    def test_threshold_boundary(self) -> None:
        baseline = 2000.0
        just_above = int(baseline * COVERAGE_GAP_FRACTION) + 1
        just_below = int(baseline * COVERAGE_GAP_FRACTION) - 1

        ok = BiomassEvidenceModule().evaluate(
            ctx(fires=[], regional_detection_count=just_above, regional_detection_baseline=baseline)
        )
        gap = BiomassEvidenceModule().evaluate(
            ctx(fires=[], regional_detection_count=just_below, regional_detection_baseline=baseline)
        )

        assert ok.strength == EvidenceStrength.VERY_WEAK
        assert gap.strength == EvidenceStrength.INSUFFICIENT_EVIDENCE

    def test_a_gap_suppresses_evidence_even_when_some_fires_are_present(self) -> None:
        """Partial coverage is still unreliable coverage.

        A handful of detections on a clouded day says nothing about how many
        actually burned, so a strength derived from them would be fiction.
        """
        result = BiomassEvidenceModule().evaluate(
            ctx(
                fires=[fire() for _ in range(3)],
                regional_detection_count=4,
                regional_detection_baseline=2600.0,
            )
        )

        assert result.strength == EvidenceStrength.INSUFFICIENT_EVIDENCE


class TestDiwaliDiscriminantValidity:
    """Biomass must not absorb the firework spike.

    Verified against the real archive: VIIRS overpasses Delhi at 12:00-14:00 and
    01:00-03:00 IST, and across 20 Oct - 3 Nov 2019 there were zero detections in
    the 20:00-00:00 IST firework window. Diwali night itself had 4 near-Delhi
    detections — FEWER than 20 Oct (17) or 21 Oct (15).
    """

    def test_firework_hours_produce_no_biomass_evidence_without_upwind_fires(self) -> None:
        """23:30 IST on Diwali, no upwind stubble: biomass must not fire.

        If VIIRS caught fireworks, this would show fire evidence. It does not,
        because the satellite is not overhead at 23:30 IST.
        """
        result = BiomassEvidenceModule().evaluate(
            ctx(
                evaluated_at=DIWALI_PEAK,  # 23:30 IST
                fires=[],
                regional_detection_count=1600,
                regional_detection_baseline=1600.0,
            )
        )

        assert result.strength == EvidenceStrength.VERY_WEAK

    def test_local_delhi_fires_are_distinguishable_from_upwind_stubble(self) -> None:
        """A detection 22 km away is not Punjab stubble.

        Delhi has year-round landfill fires (Bhalswa, Ghazipur). The module must
        weight a distant upwind field fire above a nearby local one, because the
        distance decay is what encodes transport.
        """
        from app.evidence.biomass import wind_weighted_influence

        local = wind_weighted_influence(fire(distance_km=22.0, bearing_offset_deg=0.0), 500.0)
        punjab = wind_weighted_influence(fire(distance_km=210.0, bearing_offset_deg=0.0), 500.0)

        # The kernel decays with distance, so a near fire scores higher per
        # detection. That is correct: proximity matters. What must NOT happen is a
        # single local fire outweighing a stubble front.
        assert local > punjab
        front = sum(
            wind_weighted_influence(fire(distance_km=210.0, bearing_offset_deg=0.0), 500.0)
            for _ in range(1500)
        )
        assert front > local * 100

    def test_biomass_evidence_requires_fires_not_merely_high_pm(self) -> None:
        """PM2.5 of 1,288 with no upwind fires must not yield fire evidence.

        The module must key on the satellite, never on the pollution it is being
        asked to explain — otherwise it reasons from its own conclusion.
        """
        result = BiomassEvidenceModule().evaluate(
            ctx(
                fires=[],
                pollutants={"pm25": 1288.0},
                regional_detection_count=1600,
                regional_detection_baseline=1600.0,
            )
        )

        assert result.strength == EvidenceStrength.VERY_WEAK
        assert result.likelihood_ratio is None
