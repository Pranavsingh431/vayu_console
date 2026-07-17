"""The Officer Decision Engine's contract.

The governing test for everything in this package: **could a pollution control
officer defend this in a meeting?** If not, it does not exist.

Constraints inherited from the Evidence Engine and the Phase 2 research:

* No probabilities. No confidence scores. A recommendation carries a
  `confidence_note` — prose an officer can read aloud — not a number that implies
  a precision we do not have.
* No recommendation without supporting evidence. Absence of evidence never
  generates advice: the biomass module can report "no fires" on a day the
  satellite simply did not pass over, so "weak fire evidence" must never be read
  as "therefore it is traffic".
* Every recommendation carries its decision trace, so the officer can walk
  backwards from the advice to the observation.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.evidence.schemas.evidence import EvidenceQuality, Observation


class RecommendationCategory(StrEnum):
    """The only categories the engine may emit. Fixed by the Phase 4 brief."""

    ROAD_TRAFFIC = "road_traffic"
    CONSTRUCTION = "construction"
    INDUSTRIAL_MONITORING = "industrial_monitoring"
    PUBLIC_HEALTH = "public_health"
    EMERGENCY_RESPONSE = "emergency_response"
    MONITORING_ONLY = "monitoring_only"


class Policy(StrEnum):
    """Reusable policy families. Rules map evidence to a policy; a policy maps to
    recommendations. Keeping the layers apart means a rule change does not rewrite
    the advice, and new advice does not rewrite the rules.
    """

    EMERGENCY_RESPONSE = "EMERGENCY_RESPONSE"
    PUBLIC_HEALTH = "PUBLIC_HEALTH"
    TRAFFIC_MANAGEMENT = "TRAFFIC_MANAGEMENT"
    MONITORING = "MONITORING"
    NO_ACTION = "NO_ACTION"


class Priority(StrEnum):
    """Operational urgency. Not a probability, and not a severity of pollution —
    a statement about how soon an officer should act.
    """

    IMMEDIATE = "immediate"
    HIGH = "high"
    ROUTINE = "routine"
    INFORMATIONAL = "informational"


class OverallStatus(StrEnum):
    """The report's headline.

    `NO_RECOMMENDATION` and `INSUFFICIENT_EVIDENCE` are distinct: the first means
    we looked and nothing warrants action, the second means we could not look.
    Collapsing them would let a blind sensor read as a clean bill of health.
    """

    ACTION_RECOMMENDED = "action_recommended"
    MONITOR = "monitor"
    NO_RECOMMENDATION = "no_recommendation"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class DecisionTraceStep(StrEnum):
    """The stages a recommendation passes through, in order."""

    EVIDENCE = "evidence"
    RULE = "rule"
    POLICY = "policy"
    RECOMMENDATION = "recommendation"


class TraceEntry(BaseModel):
    """One step of the audit trail from observation to advice."""

    model_config = ConfigDict(frozen=True)

    step: DecisionTraceStep
    identifier: str = Field(description="e.g. 'biomass', 'FIRE_001', 'EMERGENCY_RESPONSE'.")
    detail: str = Field(description="What was true at this step, in plain language.")


class Recommendation(BaseModel):
    """One action, and everything needed to defend it.

    `confidence_note` is deliberately prose. A number here would imply we can
    quantify how likely the recommendation is to be right, which would require the
    source apportionment we established is unobservable (inference.md §1).
    """

    model_config = ConfigDict(use_enum_values=True)

    id: str = Field(description="Catalogue id, e.g. 'REC_SPRINKLER'.")
    title: str
    category: RecommendationCategory
    priority: Priority
    action: str = Field(description="What to do, concretely enough to task someone with.")
    reason: str = Field(description="Why the evidence supports this action.")

    supporting_evidence: list[Observation] = Field(default_factory=list)
    # Never optional. An officer challenged in a meeting needs to know what argues
    # against their action before someone else tells them.
    contradicting_evidence: list[Observation] = Field(default_factory=list)

    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    confidence_note: str = Field(
        description="Prose, never a number. How far this recommendation can be pushed."
    )
    references: list[str] = Field(default_factory=list)
    decision_trace: list[TraceEntry] = Field(default_factory=list)

    triggered_by_rule: str = Field(description="Rule id that produced this.")
    policy: Policy


class DecisionReport(BaseModel):
    """The engine's output for one station-hour."""

    model_config = ConfigDict(use_enum_values=True)

    timestamp: dt.datetime = Field(description="The instant being advised on (UTC).")
    generated_at: dt.datetime = Field(description="When this report was produced (UTC).")
    station: str
    station_id: int | None = None

    overall_status: OverallStatus
    summary: str
    recommendations: list[Recommendation] = Field(default_factory=list)

    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    supporting_evidence: list[Observation] = Field(default_factory=list)
    contradicting_evidence: list[Observation] = Field(default_factory=list)

    data_quality: EvidenceQuality
    requires_human_review: bool
    human_review_reasons: list[str] = Field(default_factory=list)

    decision_trace: list[TraceEntry] = Field(default_factory=list)
    conflict_note: str | None = Field(
        default=None,
        description="Set when hypotheses disagree. The engine reports both rather than picking.",
    )

    engine_version: str
    evidence_engine_version: str

    @property
    def notice(self) -> str:
        return (
            "Recommendations are derived deterministically from evidence, with no "
            "model and no language model involved. Every recommendation states the "
            "evidence for it, the evidence against it, and its assumptions. The "
            "system does not measure source contributions."
        )
