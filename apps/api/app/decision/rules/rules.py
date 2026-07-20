"""The rule engine.

Deterministic. No model, no language model, no randomness: the same Evidence
Report always yields the same Decision Report, which is what makes the advice
auditable months later.

Two invariants hold across every rule:

1. **A rule fires on the PRESENCE of evidence, never on its absence.** "Biomass
   evidence is weak" must never trigger a traffic recommendation. Weak biomass
   evidence can mean the satellite did not pass over — verified: 31 Oct 2019
   recorded 4 detections between neighbours of 2,600 and 2,612, because fires do
   not stop for a day. Reasoning from absence would have an officer act on a
   cloudy sky.

2. **A rule never picks between competing hypotheses.** If two are strong, both
   sets of recommendations are emitted and the conflict is reported. Choosing
   would be apportionment by the back door.
"""

from __future__ import annotations

import datetime as dt
from collections.abc import Callable
from dataclasses import dataclass

from app.decision.schemas.decision import Policy
from app.evidence.schemas.evidence import (
    EvidenceQuality,
    EvidenceReport,
    EvidenceResult,
    EvidenceStrength,
    Hypothesis,
    hypothesis_prose,
    quality_prose,
)

# Ranks for comparing strengths. INSUFFICIENT sits below VERY_WEAK because it is
# not a weak finding — it is no finding.
_RANK: dict[str, int] = {
    EvidenceStrength.INSUFFICIENT_EVIDENCE.value: -1,
    EvidenceStrength.VERY_WEAK.value: 0,
    EvidenceStrength.WEAK.value: 1,
    EvidenceStrength.MODERATE.value: 2,
    EvidenceStrength.STRONG.value: 3,
    EvidenceStrength.VERY_STRONG.value: 4,
}

MORNING_PEAK = (7, 11)
EVENING_PEAK = (17, 21)
IST = dt.timezone(dt.timedelta(hours=5, minutes=30))


def rank(strength: str) -> int:
    return _RANK.get(str(strength), -1)


def at_least(result: EvidenceResult | None, strength: EvidenceStrength) -> bool:
    """Whether a hypothesis reached at least `strength`. Missing means no."""
    return result is not None and rank(str(result.strength)) >= _RANK[strength.value]


def at_most(result: EvidenceResult | None, strength: EvidenceStrength) -> bool:
    """Whether a hypothesis is at most `strength`, having actually been judged.

    Insufficient evidence returns False: a hypothesis we could not judge is not
    "at most weak", it is unknown, and treating unknown as low is how absence
    turns into a conclusion.
    """
    if result is None or str(result.strength) == EvidenceStrength.INSUFFICIENT_EVIDENCE.value:
        return False
    return rank(str(result.strength)) <= _RANK[strength.value]


def is_insufficient(result: EvidenceResult | None) -> bool:
    return result is None or str(result.strength) == EvidenceStrength.INSUFFICIENT_EVIDENCE.value


@dataclass(frozen=True, slots=True)
class RuleContext:
    """What a rule may inspect. Only the Evidence Report — never raw data."""

    report: EvidenceReport

    def get(self, hypothesis: Hypothesis) -> EvidenceResult | None:
        for result in self.report.evidence:
            if str(result.hypothesis) == hypothesis.value:
                return result
        return None

    @property
    def ist_hour(self) -> int:
        return self.report.evaluated_at.astimezone(IST).hour

    @property
    def in_commute_peak(self) -> bool:
        h = self.ist_hour
        return MORNING_PEAK[0] <= h <= MORNING_PEAK[1] or EVENING_PEAK[0] <= h <= EVENING_PEAK[1]


@dataclass(frozen=True, slots=True)
class Rule:
    """One deterministic evidence-to-policy mapping."""

    id: str
    description: str
    #: Why an officer could defend the resulting action. The rule's justification.
    defensible_because: str
    policy: Policy
    condition: Callable[[RuleContext], bool]
    recommendation_ids: tuple[str, ...]
    #: What this rule explicitly declines to conclude. Prevents over-reading.
    does_not_imply: str = ""

    def fires(self, context: RuleContext) -> bool:
        return self.condition(context)


# --------------------------------------------------------------------------
# Biomass rules
# --------------------------------------------------------------------------

FIRE_001 = Rule(
    id="FIRE_001",
    description="Strong biomass evidence with traffic evidence no greater than weak.",
    defensible_because=(
        "Fires were observed upwind by satellite — a signal independent of the "
        "monitor being explained. An officer can point at the detections, the wind "
        "direction and the timing, none of which are inferences from our own sensor."
    ),
    policy=Policy.EMERGENCY_RESPONSE,
    condition=lambda c: (
        at_least(c.get(Hypothesis.BIOMASS), EvidenceStrength.STRONG)
        and at_most(c.get(Hypothesis.TRAFFIC), EvidenceStrength.WEAK)
    ),
    recommendation_ids=("REC_SPRINKLER", "REC_PUBLIC_ADVISORY", "REC_INCREASE_MONITORING"),
    does_not_imply=(
        "Does NOT imply traffic is not contributing — only that traffic evidence "
        "is weaker. It does not license traffic restrictions, and it does not "
        "quantify the fire contribution."
    ),
)

FIRE_002 = Rule(
    id="FIRE_002",
    description="Moderate biomass evidence.",
    defensible_because=(
        "Upwind fires are observed but the influence is not decisive. An advisory "
        "and closer observation are proportionate; committing the sprinkling fleet "
        "is not."
    ),
    policy=Policy.PUBLIC_HEALTH,
    condition=lambda c: (
        at_least(c.get(Hypothesis.BIOMASS), EvidenceStrength.MODERATE)
        and not at_least(c.get(Hypothesis.BIOMASS), EvidenceStrength.STRONG)
    ),
    recommendation_ids=("REC_PUBLIC_ADVISORY", "REC_INCREASE_MONITORING"),
    does_not_imply="Does NOT justify emergency resource deployment.",
)

# --------------------------------------------------------------------------
# Traffic rules
# --------------------------------------------------------------------------

TRAFFIC_001 = Rule(
    id="TRAFFIC_001",
    description="Moderate traffic evidence during a commute peak.",
    defensible_because=(
        "Two independent things agree: the NO2/SO2 ratio sits in the regime the "
        "COVID lockdown associated with normal traffic, AND the hour is a commute "
        "peak. Enforcement is defensible as routine activity even if the "
        "attribution is wrong, which is why it is priced ROUTINE."
    ),
    policy=Policy.TRAFFIC_MANAGEMENT,
    condition=lambda c: (
        at_least(c.get(Hypothesis.TRAFFIC), EvidenceStrength.MODERATE) and c.in_commute_peak
    ),
    recommendation_ids=(
        "REC_TRAFFIC_ENFORCEMENT",
        "REC_TRAFFIC_COORDINATION",
        "REC_INCREASE_MONITORING",
    ),
    does_not_imply=(
        "Does NOT imply traffic is the dominant source. The traffic hypothesis is "
        "weakly identified (LR 2.11) and has no signal exogenous to the monitor."
    ),
)

# Deliberately NO rule for "traffic strong outside a commute peak". The traffic
# module caps at MODERATE by construction, and elevated NO2 at 23:00 IST is not a
# commute profile — the module reports that hour as contradicting evidence. A rule
# recommending rush-hour enforcement at midnight is not defensible.

# --------------------------------------------------------------------------
# Industrial rules
# --------------------------------------------------------------------------

INDUSTRIAL_001 = Rule(
    id="INDUSTRIAL_001",
    description="Industrial evidence present and at least weak, with SO2 actually measured.",
    defensible_because=(
        "An elevated SO2 reading is a real observation and warrants a human look. "
        "It does not warrant enforcement: no experiment isolates industry, so the "
        "module carries no likelihood ratio and cannot attribute the reading."
    ),
    policy=Policy.MONITORING,
    condition=lambda c: at_least(c.get(Hypothesis.INDUSTRIAL), EvidenceStrength.WEAK),
    recommendation_ids=("REC_INDUSTRIAL_REVIEW",),
    does_not_imply=(
        "Does NOT justify inspection, restriction or enforcement against any "
        "facility. The plant's operator would be right to object."
    ),
)

# There is deliberately NO rule that fires on INSUFFICIENT industrial evidence.
# The Phase 4 brief asked for one that states no intervention is justified — the
# engine does state that, but as a report-level note rather than a recommendation.
# A "recommendation" to do nothing is not an action, and putting it in the
# recommendation list would pad the list while telling the officer nothing.

# --------------------------------------------------------------------------

ALL_RULES: tuple[Rule, ...] = (FIRE_001, FIRE_002, TRAFFIC_001, INDUSTRIAL_001)


class RuleEngine:
    """Evaluates rules against an Evidence Report. Deterministic and order-stable."""

    def __init__(self, rules: tuple[Rule, ...] = ALL_RULES) -> None:
        self._rules = rules

    @property
    def rules(self) -> tuple[Rule, ...]:
        return self._rules

    def evaluate(self, report: EvidenceReport) -> list[Rule]:
        """Return every rule that fires, in declaration order."""
        context = RuleContext(report=report)
        return [rule for rule in self._rules if rule.fires(context)]


def detect_conflict(report: EvidenceReport) -> str | None:
    """Report competing strong hypotheses rather than choosing between them.

    Two hypotheses can both be strong and both be right: on a Diwali night in
    stubble season, fireworks and transported smoke arrive together. Picking one
    would be apportionment.
    """
    strong = [
        hypothesis_prose(r.hypothesis)
        for r in report.evidence
        if at_least(r, EvidenceStrength.MODERATE)
    ]
    if len(strong) < 2:
        return None
    return (
        f"Multiple plausible contributors detected ({', '.join(sorted(strong))}). "
        "Recommended actions address each hypothesis independently; the engine does "
        "not choose between them, because the evidence does not. Further "
        "investigation advised."
    )


def human_review_reasons(report: EvidenceReport, fired: list[Rule]) -> list[str]:
    """Why a human must look at this before it is acted on.

    Each condition is a case where the engine's output is either unreliable or
    incomplete, and acting on it unreviewed would put the officer at risk.
    """
    reasons: list[str] = []

    if str(report.overall_quality) in {EvidenceQuality.POOR.value, EvidenceQuality.NO_DATA.value}:
        reasons.append(
            f"Data quality is {quality_prose(report.overall_quality)}. The evidence may be based on "
            "sparse or missing observations."
        )

    if detect_conflict(report):
        reasons.append(
            "Multiple hypotheses have moderate or stronger evidence. The engine "
            "cannot separate them and does not try."
        )

    insufficient = [hypothesis_prose(r.hypothesis) for r in report.evidence if is_insufficient(r)]
    if insufficient:
        reasons.append(
            f"Required observations are missing for: {', '.join(sorted(insufficient))}. "
            "This is not evidence that those sources are absent."
        )

    pending = {
        v.experiment
        for r in report.evidence
        for v in r.historical_validation
        if str(v.status) == "pending"
    }
    if pending:
        reasons.append(
            f"Historical validation is still pending for: {', '.join(sorted(pending))}. "
            "Those modules have not yet survived a test that could reject them."
        )

    if not fired:
        reasons.append(
            "No rule reached an actionable recommendation. The engine has nothing to "
            "suggest, which is not the same as there being nothing to do."
        )

    return reasons
