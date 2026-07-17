"""Tests for the evidence aggregator.

The constraints pinned here are the ones that keep the engine from quietly
becoming a classifier: no normalisation, no probabilities, and a report that
survives a module blowing up.
"""

from __future__ import annotations

import datetime as dt

import pytest

from app.evidence import EvidenceAggregator, EvidenceContext, FireObservation
from app.evidence.base import EvidenceModule
from app.evidence.schemas import (
    EvidenceQuality,
    EvidenceResult,
    EvidenceStrength,
    Hypothesis,
    Identification,
)

DIWALI_PEAK = dt.datetime(2019, 10, 27, 18, 0, tzinfo=dt.UTC)


def full_context() -> EvidenceContext:
    """Diwali 2019 at Anand Vihar: the confounded case the engine exists for."""
    return EvidenceContext(
        station_name="Anand Vihar",
        station_id=235,
        evaluated_at=DIWALI_PEAK,
        pollutants={"no2": 64.0, "so2": 11.0, "pm25": 1288.0},
        wind_direction_deg=315.0,
        wind_speed_ms=4.0,
        boundary_layer_height_m=210.0,
        fires_queried=True,
        fires=[
            FireObservation(
                latitude=30.2,
                longitude=76.4,
                acquired_at=DIWALI_PEAK - dt.timedelta(hours=6),
                frp_mw=45.0,
                confidence="h",
                distance_km=210.0,
                bearing_offset_deg=12.0,
                source="firms_viirs_snpp_sp",
            )
            for _ in range(30)
        ],
    )


class TestAggregator:
    def test_every_hypothesis_is_reported(self) -> None:
        report = EvidenceAggregator().evaluate(full_context())

        assert {str(e.hypothesis) for e in report.evidence} == {
            Hypothesis.BIOMASS.value,
            Hypothesis.TRAFFIC.value,
            Hypothesis.INDUSTRIAL.value,
        }

    def test_strengths_are_not_normalised(self) -> None:
        """The central constraint. Hypotheses are not mutually exclusive.

        On a Diwali night in stubble season, biomass and traffic evidence are both
        legitimately present. Anything summing to 1 is apportionment in disguise.
        """
        report = EvidenceAggregator().evaluate(full_context())
        lrs = [e.likelihood_ratio for e in report.evidence if e.likelihood_ratio is not None]

        assert lrs
        assert sum(lrs) != pytest.approx(1.0)

    def test_report_contains_no_probabilities_or_percentages(self) -> None:
        blob = EvidenceAggregator().evaluate(full_context()).model_dump_json()

        assert "probability" not in blob.lower()
        assert "percent" not in blob.lower()

    def test_overall_quality_is_the_worst_judged_module(self) -> None:
        """A report is only as trustworthy as its weakest judged component."""
        report = EvidenceAggregator().evaluate(full_context())

        judged = [
            e
            for e in report.evidence
            if str(e.strength) != EvidenceStrength.INSUFFICIENT_EVIDENCE.value
        ]
        qualities = {str(e.evidence_quality) for e in judged}
        assert str(report.overall_quality) in qualities

    def test_empty_context_yields_insufficient_everywhere_not_a_clean_bill(self) -> None:
        report = EvidenceAggregator().evaluate(
            EvidenceContext(station_name="Nowhere", evaluated_at=DIWALI_PEAK)
        )

        assert all(
            str(e.strength) == EvidenceStrength.INSUFFICIENT_EVIDENCE.value for e in report.evidence
        )
        assert report.overall_quality == EvidenceQuality.NO_DATA
        assert "not evidence that the air is clean" in report.summary

    def test_summary_names_the_hypotheses_it_could_not_judge(self) -> None:
        report = EvidenceAggregator().evaluate(
            EvidenceContext(
                station_name="Partial",
                evaluated_at=DIWALI_PEAK,
                pollutants={"no2": 60.0},  # no SO2, no fires queried
            )
        )

        assert "Could not judge" in report.summary
        assert "not evidence of absence" in report.summary

    def test_a_failing_module_does_not_take_down_the_report(self) -> None:
        """One defect must not cost the officer the evidence that did resolve."""

        class ExplodingModule(EvidenceModule):
            name = "exploding"
            hypothesis = Hypothesis.TRAFFIC
            identification = Identification.WEAK

            def evaluate(self, context: EvidenceContext) -> EvidenceResult:
                raise RuntimeError("boom")

        report = EvidenceAggregator(modules=[ExplodingModule()]).evaluate(full_context())

        assert len(report.evidence) == 1
        assert str(report.evidence[0].strength) == EvidenceStrength.INSUFFICIENT_EVIDENCE.value
        assert any("defect, not a finding" in limit for limit in report.evidence[0].limitations)

    def test_provenance_is_recorded(self) -> None:
        report = EvidenceAggregator().evaluate(full_context())

        assert report.engine_version
        assert report.generated_at.tzinfo is not None
        assert report.evaluated_at == DIWALI_PEAK
        assert "openaq_s3" in report.data_sources

    def test_notice_disclaims_apportionment(self) -> None:
        report = EvidenceAggregator().evaluate(full_context())

        assert "does not measure source contributions" in report.notice

    def test_modules_are_replaceable(self) -> None:
        """Composability: the aggregator knows only the interface."""

        class StubModule(EvidenceModule):
            name = "stub"
            hypothesis = Hypothesis.BIOMASS
            identification = Identification.STRONG

            def evaluate(self, context: EvidenceContext) -> EvidenceResult:
                return self._result(EvidenceStrength.STRONG, EvidenceQuality.HIGH)

        report = EvidenceAggregator(modules=[StubModule()]).evaluate(full_context())

        assert len(report.evidence) == 1
        assert report.evidence[0].name == "stub"


class TestEvidenceContext:
    def test_negative_sentinels_are_not_treated_as_present(self) -> None:
        """The archive carries -999 sentinels; a module must never reason over one."""
        context = EvidenceContext(
            station_name="S", evaluated_at=DIWALI_PEAK, pollutants={"pm25": -999.0, "no2": 40.0}
        )

        assert context.has("no2")
        assert not context.has("pm25")
        assert not context.has("no2", "pm25")

    def test_ist_hour_converts_from_utc(self) -> None:
        """Diwali's peak is an IST phenomenon; reading UTC shifts it 5.5 hours."""
        context = EvidenceContext(station_name="S", evaluated_at=DIWALI_PEAK)

        assert context.ist_hour() == 23
