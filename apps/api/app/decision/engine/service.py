"""The Officer Decision Engine.

Consumes an Evidence Report and produces a Decision Report. Touches no raw data:
if a fact is not in the Evidence Report, the engine cannot use it, which is what
guarantees every recommendation traces back to observed evidence.
"""

from __future__ import annotations

import datetime as dt
import logging

from app.decision.recommendations.catalogue import CATALOGUE, CatalogueEntry
from app.decision.rules.rules import (
    Rule,
    RuleEngine,
    detect_conflict,
    human_review_reasons,
    is_insufficient,
)
from app.decision.schemas.decision import (
    DecisionReport,
    DecisionTraceStep,
    OverallStatus,
    Policy,
    Recommendation,
    TraceEntry,
)
from app.evidence.schemas.evidence import (
    EvidenceQuality,
    EvidenceReport,
    EvidenceResult,
    Hypothesis,
    Observation,
    hypothesis_prose,
)

logger = logging.getLogger(__name__)

ENGINE_VERSION = "0.1.0"

#: Which hypothesis each rule reasons from, for attaching evidence to advice.
_RULE_HYPOTHESIS: dict[str, Hypothesis] = {
    "FIRE_001": Hypothesis.BIOMASS,
    "FIRE_002": Hypothesis.BIOMASS,
    "TRAFFIC_001": Hypothesis.TRAFFIC,
    "INDUSTRIAL_001": Hypothesis.INDUSTRIAL,
}


class DecisionEngine:
    """Turns evidence into defensible, traceable recommendations."""

    def __init__(self, rule_engine: RuleEngine | None = None) -> None:
        self._rules = rule_engine or RuleEngine()

    @property
    def rule_engine(self) -> RuleEngine:
        return self._rules

    def evaluate(self, report: EvidenceReport) -> DecisionReport:
        fired = self._rules.evaluate(report)
        conflict = detect_conflict(report)
        review_reasons = human_review_reasons(report, fired)

        recommendations: list[Recommendation] = []
        seen: set[str] = set()
        for rule in fired:
            for rec_id in rule.recommendation_ids:
                # A recommendation reached by two rules is emitted once, attributed
                # to the first. Listing it twice would inflate the list without
                # adding information.
                if rec_id in seen:
                    continue
                entry = CATALOGUE.get(rec_id)
                if entry is None:
                    logger.error("unknown recommendation id", extra={"rec_id": rec_id})
                    continue
                seen.add(rec_id)
                recommendations.append(self._build(entry, rule, report))

        status = self._status(recommendations, report, fired)

        return DecisionReport(
            timestamp=report.evaluated_at,
            generated_at=dt.datetime.now(dt.UTC),
            station=report.station,
            station_id=report.station_id,
            overall_status=status,
            summary=self._summarise(status, recommendations, report, conflict),
            recommendations=recommendations,
            assumptions=list(report.assumptions),
            limitations=self._limitations(report, recommendations),
            supporting_evidence=[o for r in report.evidence for o in r.supporting_observations],
            contradicting_evidence=[
                o for r in report.evidence for o in r.contradicting_observations
            ],
            data_quality=EvidenceQuality(str(report.overall_quality)),
            requires_human_review=bool(review_reasons),
            human_review_reasons=review_reasons,
            decision_trace=self._report_trace(report, fired),
            conflict_note=conflict,
            engine_version=ENGINE_VERSION,
            evidence_engine_version=report.engine_version,
        )

    def _build(self, entry: CatalogueEntry, rule: Rule, report: EvidenceReport) -> Recommendation:
        """Attach the evidence that justifies a catalogue entry."""
        hypothesis = _RULE_HYPOTHESIS.get(rule.id)
        result = self._find(report, hypothesis) if hypothesis else None

        supporting: list[Observation] = list(result.supporting_observations) if result else []
        # Carried through deliberately. An officer challenged in a meeting needs to
        # know what argues against the action before someone else raises it.
        contradicting: list[Observation] = list(result.contradicting_observations) if result else []

        reason = entry.rationale
        if rule.does_not_imply:
            reason = f"{reason}\n\nScope: {rule.does_not_imply}"

        return Recommendation(
            id=entry.id,
            title=entry.title,
            category=entry.category,
            priority=entry.priority,
            action=entry.action,
            reason=reason,
            supporting_evidence=supporting,
            contradicting_evidence=contradicting,
            assumptions=list(result.assumptions) if result else [],
            limitations=list(entry.limitations) + (list(result.limitations) if result else []),
            confidence_note=entry.confidence_note,
            references=list(entry.references) + (list(result.references) if result else []),
            decision_trace=self._trace(entry, rule, result),
            triggered_by_rule=rule.id,
            policy=entry.policy,
        )

    @staticmethod
    def _find(report: EvidenceReport, hypothesis: Hypothesis | None) -> EvidenceResult | None:
        if hypothesis is None:
            return None
        for result in report.evidence:
            if str(result.hypothesis) == hypothesis.value:
                return result
        return None

    @staticmethod
    def _trace(
        entry: CatalogueEntry, rule: Rule, result: EvidenceResult | None
    ) -> list[TraceEntry]:
        """Evidence -> Rule -> Policy -> Recommendation, walkable backwards."""
        steps: list[TraceEntry] = []
        if result is not None:
            steps.append(
                TraceEntry(
                    step=DecisionTraceStep.EVIDENCE,
                    identifier=str(result.hypothesis),
                    detail=(
                        f"{result.hypothesis} evidence: {result.strength} {result.stars} "
                        f"(quality {result.evidence_quality}, identification "
                        f"{result.identification})"
                    ),
                )
            )
        steps.append(
            TraceEntry(
                step=DecisionTraceStep.RULE,
                identifier=rule.id,
                detail=f"{rule.description} Defensible because: {rule.defensible_because}",
            )
        )
        steps.append(
            TraceEntry(
                step=DecisionTraceStep.POLICY,
                identifier=str(entry.policy),
                detail=f"Policy {entry.policy} applies.",
            )
        )
        steps.append(
            TraceEntry(
                step=DecisionTraceStep.RECOMMENDATION,
                identifier=entry.id,
                detail=entry.title,
            )
        )
        return steps

    @staticmethod
    def _report_trace(report: EvidenceReport, fired: list[Rule]) -> list[TraceEntry]:
        """Report-level trace: every hypothesis considered, every rule evaluated."""
        steps = [
            TraceEntry(
                step=DecisionTraceStep.EVIDENCE,
                identifier=str(r.hypothesis),
                detail=f"{r.strength} {r.stars} (quality {r.evidence_quality})",
            )
            for r in report.evidence
        ]
        if fired:
            steps += [
                TraceEntry(step=DecisionTraceStep.RULE, identifier=r.id, detail=r.description)
                for r in fired
            ]
        else:
            steps.append(
                TraceEntry(
                    step=DecisionTraceStep.RULE,
                    identifier="none",
                    detail="No rule fired: the evidence does not support any recommendation.",
                )
            )
        return steps

    @staticmethod
    def _status(
        recommendations: list[Recommendation], report: EvidenceReport, fired: list[Rule]
    ) -> OverallStatus:
        """The headline.

        `INSUFFICIENT_EVIDENCE` and `NO_RECOMMENDATION` are kept apart: the first
        means we could not look, the second that we looked and nothing warrants
        action. Merging them would let a blind sensor read as a clean bill of health.
        """
        if all(is_insufficient(r) for r in report.evidence):
            return OverallStatus.INSUFFICIENT_EVIDENCE
        if not recommendations:
            return OverallStatus.NO_RECOMMENDATION
        if any(str(r.policy) == Policy.EMERGENCY_RESPONSE.value for r in recommendations):
            return OverallStatus.ACTION_RECOMMENDED
        if all(str(r.policy) == Policy.MONITORING.value for r in recommendations):
            return OverallStatus.MONITOR
        return OverallStatus.ACTION_RECOMMENDED

    @staticmethod
    def _summarise(
        status: OverallStatus,
        recommendations: list[Recommendation],
        report: EvidenceReport,
        conflict: str | None,
    ) -> str:
        if status == OverallStatus.INSUFFICIENT_EVIDENCE:
            return (
                "No recommendation can be justified: the observations required to "
                "judge any hypothesis are missing. This is not evidence that the air "
                "is clean, or that no action is needed — it means the system cannot see."
            )
        if status == OverallStatus.NO_RECOMMENDATION:
            return (
                "The evidence was judged but does not support any recommendation in "
                "the catalogue. No action is proposed. This is a statement about the "
                "evidence, not a clean bill of health."
            )
        lead = f"{len(recommendations)} recommendation(s) supported by evidence."
        if conflict:
            lead += " Multiple hypotheses are plausible; actions address each independently."
        return lead

    @staticmethod
    def _limitations(report: EvidenceReport, recommendations: list[Recommendation]) -> list[str]:
        limits = [
            "This system does not measure source contributions. Recommendations are "
            "derived from evidence for competing hypotheses, not from apportionment.",
            "Recommendations are generated by deterministic rules. No model and no "
            "language model is involved, so the same evidence always yields the same "
            "advice.",
        ]
        insufficient = [
            hypothesis_prose(r.hypothesis) for r in report.evidence if is_insufficient(r)
        ]
        if insufficient:
            limits.append(
                f"No recommendation addresses: {', '.join(sorted(insufficient))} — the "
                "required observations are missing. Absence of evidence is not "
                "evidence of absence, and the engine does not reason from it."
            )
        seen: dict[str, None] = {}
        for item in [*limits, *(limit for r in recommendations for limit in r.limitations)]:
            seen.setdefault(item, None)
        return list(seen)


def explain(recommendation: Recommendation) -> dict[str, object]:
    """Answer "Why this recommendation?" — powers the UI's Challenge feature.

    Everything an officer needs to defend, or abandon, the action.
    """
    return {
        "recommendation": recommendation.title,
        "action": recommendation.action,
        "why": recommendation.reason,
        "supporting_evidence": [
            o.model_dump(mode="json") for o in recommendation.supporting_evidence
        ],
        "contradicting_evidence": [
            o.model_dump(mode="json") for o in recommendation.contradicting_evidence
        ],
        "assumptions": recommendation.assumptions,
        "limitations": recommendation.limitations,
        "confidence_note": recommendation.confidence_note,
        "decision_trace": [t.model_dump(mode="json") for t in recommendation.decision_trace],
        "references": recommendation.references,
        "how_to_challenge": (
            "Check the contradicting evidence and the assumptions first. If an "
            "assumption does not hold at this station, the recommendation does not "
            "follow. The decision trace shows every step from observation to advice."
        ),
    }
