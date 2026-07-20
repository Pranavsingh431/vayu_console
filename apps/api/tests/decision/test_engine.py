"""Tests for the Officer Decision Engine.

The cases that matter are the refusals. An engine that invents advice from thin
evidence is the failure this layer exists to prevent, so most of what is pinned
here is what does NOT get recommended.
"""

from __future__ import annotations

import datetime as dt

from app.decision import DecisionEngine, RuleEngine, explain
from app.decision.recommendations import CATALOGUE, EMPTY_CATEGORIES
from app.decision.rules.rules import FIRE_001, TRAFFIC_001, detect_conflict
from app.decision.schemas import OverallStatus, RecommendationCategory
from app.evidence.schemas.evidence import (
    STRENGTH_STARS,
    EvidenceQuality,
    EvidenceReport,
    EvidenceResult,
    EvidenceStrength,
    HistoricalValidation,
    Hypothesis,
    Identification,
    Observation,
    ValidationStatus,
    hypothesis_prose,
)

# 18:00 UTC == 23:30 IST — Diwali's firework peak, outside any commute window.
DIWALI_PEAK = dt.datetime(2019, 10, 27, 18, 0, tzinfo=dt.UTC)
# 03:30 UTC == 09:00 IST — inside the morning commute peak.
MORNING_RUSH = dt.datetime(2019, 10, 24, 3, 30, tzinfo=dt.UTC)


def result(
    hypothesis: Hypothesis,
    strength: EvidenceStrength,
    *,
    quality: EvidenceQuality = EvidenceQuality.GOOD,
    identification: Identification = Identification.STRONG,
    validation_status: ValidationStatus = ValidationStatus.ACCEPTED,
) -> EvidenceResult:
    return EvidenceResult(
        name=hypothesis.value,
        hypothesis=hypothesis,
        status=strength,
        strength=strength,
        evidence_quality=quality,
        identification=identification,
        stars=STRENGTH_STARS[strength],
        explanation="test",
        supporting_observations=[Observation(label=f"{hypothesis} signal", source="test")],
        contradicting_observations=[Observation(label=f"{hypothesis} counter", source="test")],
        assumptions=[f"{hypothesis} assumption"],
        limitations=[f"{hypothesis} limitation"],
        historical_validation=[
            HistoricalValidation(experiment="Test", status=validation_status, detail="d")
        ],
    )


def report(
    *results: EvidenceResult,
    at: dt.datetime = DIWALI_PEAK,
    quality: EvidenceQuality = EvidenceQuality.GOOD,
) -> EvidenceReport:
    return EvidenceReport(
        station="Test Station",
        station_id=1,
        evaluated_at=at,
        generated_at=dt.datetime.now(dt.UTC),
        evidence=list(results),
        summary="test",
        overall_quality=quality,
        engine_version="0.1.0",
    )


class TestStrongFireEvidence:
    def test_strong_fire_with_weak_traffic_triggers_emergency_response(self) -> None:
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                result(Hypothesis.TRAFFIC, EvidenceStrength.WEAK),
            )
        )

        assert d.overall_status == OverallStatus.ACTION_RECOMMENDED
        ids = {r.id for r in d.recommendations}
        assert "REC_SPRINKLER" in ids
        assert "REC_PUBLIC_ADVISORY" in ids

    def test_strong_fire_does_not_recommend_traffic_restrictions(self) -> None:
        """Strong fire evidence is not a licence to act on traffic."""
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                result(Hypothesis.TRAFFIC, EvidenceStrength.WEAK),
            )
        )

        assert not [
            r
            for r in d.recommendations
            if str(r.category) == RecommendationCategory.ROAD_TRAFFIC.value
        ]

    def test_recommendation_states_what_it_does_not_imply(self) -> None:
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                result(Hypothesis.TRAFFIC, EvidenceStrength.WEAK),
            )
        )
        sprinkler = next(r for r in d.recommendations if r.id == "REC_SPRINKLER")

        assert "Scope:" in sprinkler.reason
        assert "does not quantify" in sprinkler.reason.lower()


class TestWeakFireEvidence:
    def test_weak_fire_alone_produces_no_recommendation(self) -> None:
        """Weak evidence must not produce advice."""
        d = DecisionEngine().evaluate(report(result(Hypothesis.BIOMASS, EvidenceStrength.WEAK)))

        assert d.overall_status == OverallStatus.NO_RECOMMENDATION
        assert d.recommendations == []
        assert "not a clean bill of health" in d.summary

    def test_moderate_fire_advises_but_does_not_deploy_resources(self) -> None:
        d = DecisionEngine().evaluate(report(result(Hypothesis.BIOMASS, EvidenceStrength.MODERATE)))
        ids = {r.id for r in d.recommendations}

        assert "REC_PUBLIC_ADVISORY" in ids
        assert "REC_SPRINKLER" not in ids


class TestTrafficEvidence:
    def test_moderate_traffic_in_commute_peak_triggers_traffic_management(self) -> None:
        d = DecisionEngine().evaluate(
            report(
                result(
                    Hypothesis.TRAFFIC,
                    EvidenceStrength.MODERATE,
                    identification=Identification.WEAK,
                ),
                at=MORNING_RUSH,
            )
        )
        ids = {r.id for r in d.recommendations}

        assert "REC_TRAFFIC_ENFORCEMENT" in ids

    def test_traffic_evidence_outside_commute_peak_recommends_nothing(self) -> None:
        """Rush-hour enforcement at 23:30 is not defensible, whatever NO2 says."""
        d = DecisionEngine().evaluate(
            report(
                result(
                    Hypothesis.TRAFFIC,
                    EvidenceStrength.MODERATE,
                    identification=Identification.WEAK,
                ),
                at=DIWALI_PEAK,
            )
        )

        assert not [
            r
            for r in d.recommendations
            if str(r.category) == RecommendationCategory.ROAD_TRAFFIC.value
        ]

    def test_traffic_recommendation_admits_weak_identification(self) -> None:
        d = DecisionEngine().evaluate(
            report(
                result(
                    Hypothesis.TRAFFIC,
                    EvidenceStrength.MODERATE,
                    identification=Identification.WEAK,
                ),
                at=MORNING_RUSH,
            )
        )
        rec = next(r for r in d.recommendations if r.id == "REC_TRAFFIC_ENFORCEMENT")

        assert "weakly identified" in rec.confidence_note
        assert "2.11" in rec.confidence_note


class TestIndustrialEvidence:
    def test_insufficient_industrial_produces_no_industrial_recommendation(self) -> None:
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                result(Hypothesis.TRAFFIC, EvidenceStrength.WEAK),
                result(Hypothesis.INDUSTRIAL, EvidenceStrength.INSUFFICIENT_EVIDENCE),
            )
        )

        assert not [
            r
            for r in d.recommendations
            if str(r.category) == RecommendationCategory.INDUSTRIAL_MONITORING.value
        ]

    def test_insufficient_industrial_is_stated_in_limitations(self) -> None:
        """The officer must be told we could not look, not left to infer."""
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                result(Hypothesis.TRAFFIC, EvidenceStrength.WEAK),
                result(Hypothesis.INDUSTRIAL, EvidenceStrength.INSUFFICIENT_EVIDENCE),
            )
        )

        # Named in the prose form the officer reads, not the wire identifier.
        assert any(hypothesis_prose(Hypothesis.INDUSTRIAL) in limit for limit in d.limitations)
        assert any("not evidence of absence" in limit for limit in d.limitations)

    def test_industrial_never_recommends_inspection_or_restriction(self) -> None:
        """No experiment isolates industry; enforcement is indefensible."""
        d = DecisionEngine().evaluate(
            report(
                result(
                    Hypothesis.INDUSTRIAL,
                    EvidenceStrength.WEAK,
                    identification=Identification.VERY_WEAK,
                )
            )
        )

        for rec in d.recommendations:
            assert "inspect" not in rec.action.lower() or "do not dispatch" in rec.action.lower()
            assert "shut" not in rec.action.lower()
            assert "restrict" not in rec.action.lower()


class TestConflictResolution:
    def test_two_strong_hypotheses_are_both_addressed_not_chosen_between(self) -> None:
        r = report(
            result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
            result(
                Hypothesis.TRAFFIC, EvidenceStrength.MODERATE, identification=Identification.WEAK
            ),
            at=MORNING_RUSH,
        )
        d = DecisionEngine().evaluate(r)

        assert d.conflict_note is not None
        assert "Multiple plausible contributors" in d.conflict_note
        assert "does not choose between them" in d.conflict_note

    def test_conflict_triggers_human_review(self) -> None:
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                result(
                    Hypothesis.TRAFFIC,
                    EvidenceStrength.MODERATE,
                    identification=Identification.WEAK,
                ),
                at=MORNING_RUSH,
            )
        )

        assert d.requires_human_review
        assert any("cannot separate them" in reason for reason in d.human_review_reasons)

    def test_single_strong_hypothesis_is_not_a_conflict(self) -> None:
        assert detect_conflict(report(result(Hypothesis.BIOMASS, EvidenceStrength.STRONG))) is None


class TestHumanReview:
    def test_poor_data_quality_requires_review(self) -> None:
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG), quality=EvidenceQuality.POOR
            )
        )

        assert d.requires_human_review
        assert any("Data quality is poor" in reason for reason in d.human_review_reasons)

    def test_missing_evidence_requires_review(self) -> None:
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                result(Hypothesis.INDUSTRIAL, EvidenceStrength.INSUFFICIENT_EVIDENCE),
            )
        )

        assert d.requires_human_review
        assert any("Required observations are missing" in r for r in d.human_review_reasons)

    def test_pending_historical_validation_requires_review(self) -> None:
        """A module that has not survived a test it could fail is not settled."""
        d = DecisionEngine().evaluate(
            report(
                result(
                    Hypothesis.BIOMASS,
                    EvidenceStrength.STRONG,
                    validation_status=ValidationStatus.PENDING,
                )
            )
        )

        assert d.requires_human_review
        assert any("Historical validation is still pending" in r for r in d.human_review_reasons)

    def test_no_actionable_recommendation_requires_review(self) -> None:
        d = DecisionEngine().evaluate(
            report(result(Hypothesis.BIOMASS, EvidenceStrength.VERY_WEAK))
        )

        assert d.requires_human_review
        assert any("No rule reached an actionable" in r for r in d.human_review_reasons)


class TestInsufficientEvidence:
    def test_all_insufficient_is_distinct_from_no_recommendation(self) -> None:
        """We cannot see is not the same as nothing to do."""
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.INSUFFICIENT_EVIDENCE),
                result(Hypothesis.TRAFFIC, EvidenceStrength.INSUFFICIENT_EVIDENCE),
                result(Hypothesis.INDUSTRIAL, EvidenceStrength.INSUFFICIENT_EVIDENCE),
            )
        )

        assert d.overall_status == OverallStatus.INSUFFICIENT_EVIDENCE
        assert d.recommendations == []
        assert "cannot see" in d.summary
        assert "not evidence that the air is clean" in d.summary

    def test_absence_of_evidence_never_produces_a_recommendation(self) -> None:
        """The core invariant. Weak biomass may just mean the satellite blinked:
        31 Oct 2019 logged 4 detections between neighbours of 2,600 and 2,612."""
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.VERY_WEAK),
                result(
                    Hypothesis.TRAFFIC,
                    EvidenceStrength.VERY_WEAK,
                    identification=Identification.WEAK,
                ),
                at=MORNING_RUSH,
            )
        )

        assert d.recommendations == []


class TestTraceability:
    def test_every_recommendation_has_a_full_trace(self) -> None:
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                result(Hypothesis.TRAFFIC, EvidenceStrength.WEAK),
            )
        )

        for rec in d.recommendations:
            steps = [str(t.step) for t in rec.decision_trace]
            assert steps == ["evidence", "rule", "policy", "recommendation"]

    def test_every_recommendation_carries_contradicting_evidence(self) -> None:
        """An officer needs the counter-argument before someone else supplies it."""
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                result(Hypothesis.TRAFFIC, EvidenceStrength.WEAK),
            )
        )

        assert all(r.contradicting_evidence for r in d.recommendations)

    def test_no_probabilities_or_percentages_anywhere(self) -> None:
        blob = (
            DecisionEngine()
            .evaluate(
                report(
                    result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                    result(Hypothesis.TRAFFIC, EvidenceStrength.WEAK),
                )
            )
            .model_dump_json()
            .lower()
        )

        assert "probability" not in blob
        assert "confidence_score" not in blob

    def test_engine_is_deterministic(self) -> None:
        """Same evidence, same advice — always. Auditable months later."""
        r = report(
            result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
            result(Hypothesis.TRAFFIC, EvidenceStrength.WEAK),
        )
        a = DecisionEngine().evaluate(r)
        b = DecisionEngine().evaluate(r)

        assert [x.id for x in a.recommendations] == [x.id for x in b.recommendations]

    def test_explain_answers_why_and_how_to_challenge(self) -> None:
        d = DecisionEngine().evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                result(Hypothesis.TRAFFIC, EvidenceStrength.WEAK),
            )
        )
        e = explain(d.recommendations[0])

        assert e["why"]
        assert e["contradicting_evidence"]
        assert e["confidence_note"]
        assert "how_to_challenge" in e


class TestCatalogue:
    def test_construction_category_is_empty_and_says_why(self) -> None:
        """No construction module exists, so construction advice would be unfounded."""
        assert RecommendationCategory.CONSTRUCTION.value in EMPTY_CATEGORIES
        assert not [
            e for e in CATALOGUE.values() if e.category == RecommendationCategory.CONSTRUCTION
        ]

    def test_every_entry_has_a_confidence_note_not_a_score(self) -> None:
        for entry in CATALOGUE.values():
            assert entry.confidence_note
            assert not hasattr(entry, "confidence_score")

    def test_every_rule_declares_why_it_is_defensible(self) -> None:
        for rule in RuleEngine().rules:
            assert rule.defensible_because, f"{rule.id} must justify itself"

    def test_rules_reference_only_real_recommendations(self) -> None:
        for rule in RuleEngine().rules:
            for rec_id in rule.recommendation_ids:
                assert rec_id in CATALOGUE, f"{rule.id} references unknown {rec_id}"

    def test_fire_and_traffic_rules_are_modular(self) -> None:
        """Rules are replaceable without touching the engine."""
        d = DecisionEngine(rule_engine=RuleEngine(rules=(FIRE_001,))).evaluate(
            report(
                result(Hypothesis.BIOMASS, EvidenceStrength.STRONG),
                result(
                    Hypothesis.TRAFFIC,
                    EvidenceStrength.MODERATE,
                    identification=Identification.WEAK,
                ),
                at=MORNING_RUSH,
            )
        )

        assert all(r.triggered_by_rule == "FIRE_001" for r in d.recommendations)
        assert TRAFFIC_001 not in RuleEngine(rules=(FIRE_001,)).rules
