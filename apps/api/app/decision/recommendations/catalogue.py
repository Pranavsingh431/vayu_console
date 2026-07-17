"""The recommendation catalogue.

Every entry here was written against one test: **could a pollution control officer
defend this in a meeting?** Several obvious-sounding recommendations were left out
because the answer was no:

* *"Halt construction"* — we have no construction evidence module at all. Phase 2
  restricted the hypotheses to biomass, traffic and industrial. Recommending a
  construction ban would be advice with no evidence behind it, which is the exact
  failure this engine exists to prevent. The CONSTRUCTION category therefore has
  no entries until a construction module exists and passes a stress test.
* *"Close schools"* — a serious civic action. Justifying it needs a health
  exposure threshold we have not established, and PM2.5 alone does not carry one
  that an officer could cite.
* *"Ban stubble burning"* — outside Delhi's jurisdiction. An officer cannot act on
  it, so it is not a recommendation, it is a complaint.

What remains is deliberately small. Optimise for transparency, not quantity.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.decision.schemas.decision import Policy, Priority, RecommendationCategory


@dataclass(frozen=True, slots=True)
class CatalogueEntry:
    """A recommendation template, before evidence is attached."""

    id: str
    title: str
    category: RecommendationCategory
    policy: Policy
    priority: Priority
    action: str
    #: Why this is warranted. The rule supplies the evidence; this supplies the logic.
    rationale: str
    #: What must hold for this to apply at all. Enforced by rules, stated here.
    applicable_conditions: str
    confidence_note: str
    limitations: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)


# --------------------------------------------------------------------------
# EMERGENCY_RESPONSE — biomass
# --------------------------------------------------------------------------

SPRINKLERS = CatalogueEntry(
    id="REC_SPRINKLER",
    title="Deploy roadside water sprinklers on arterial routes",
    category=RecommendationCategory.EMERGENCY_RESPONSE,
    policy=Policy.EMERGENCY_RESPONSE,
    priority=Priority.HIGH,
    action=(
        "Task the mechanical sprinkling fleet to arterial roads in the affected "
        "zone for the next 12 hours, prioritising routes nearest the reporting station."
    ),
    rationale=(
        "Sprinkling suppresses resuspension of deposited particulate. It does not "
        "stop transported smoke arriving, but it prevents already-settled material "
        "being lifted back into the air by traffic — which is the part of the "
        "problem a municipal officer can actually act on during a transport episode."
    ),
    applicable_conditions="Strong biomass evidence, i.e. fires observed upwind by satellite.",
    confidence_note=(
        "Defensible as a mitigation of local resuspension. It is NOT a claim that "
        "sprinkling reduces transported smoke, and the expected magnitude of "
        "benefit has not been quantified from our data."
    ),
    limitations=[
        "The system cannot estimate how much PM2.5 this will remove. No such "
        "estimate is possible from our data — see inference.md §1.",
        "Effectiveness against fine PM2.5 (as opposed to coarse PM10) is contested "
        "in the literature and is not established here.",
    ],
    references=["CPCB GRAP measures; Delhi mechanical sprinkling programme."],
)

PUBLIC_ADVISORY = CatalogueEntry(
    id="REC_PUBLIC_ADVISORY",
    title="Issue a public health advisory for the affected zone",
    category=RecommendationCategory.PUBLIC_HEALTH,
    policy=Policy.PUBLIC_HEALTH,
    priority=Priority.HIGH,
    action=(
        "Issue an advisory recommending that residents limit outdoor exertion and "
        "that sensitive groups remain indoors while concentrations stay elevated."
    ),
    rationale=(
        "An advisory is defensible on the measured concentration alone. It does not "
        "depend on knowing the source, which is why it survives even when the "
        "attribution evidence is weak or contested."
    ),
    applicable_conditions="Any hypothesis with at least moderate evidence, or a confirmed episode.",
    confidence_note=(
        "The strongest recommendation this engine makes, because it rests on a "
        "measured concentration rather than on an inferred source."
    ),
    limitations=[
        "The advisory does not reduce emissions. It transfers risk management to " "residents.",
    ],
    references=["CPCB AQI health breakpoints."],
)

INCREASE_MONITORING = CatalogueEntry(
    id="REC_INCREASE_MONITORING",
    title="Increase monitoring cadence at the affected station",
    category=RecommendationCategory.MONITORING_ONLY,
    policy=Policy.MONITORING,
    priority=Priority.ROUTINE,
    action=(
        "Raise the reporting cadence at this station and its neighbours, and flag "
        "the episode for review once the window closes."
    ),
    rationale=(
        "Always defensible: it commits no resources beyond observation and cannot "
        "be wrong in the way an intervention can. It is the correct response to "
        "uncertainty."
    ),
    applicable_conditions="Any state, including insufficient evidence.",
    confidence_note="Carries no attribution claim. Recommending observation is never overreach.",
    limitations=["Does not reduce emissions or exposure."],
    references=[],
)

# --------------------------------------------------------------------------
# TRAFFIC_MANAGEMENT
# --------------------------------------------------------------------------

TRAFFIC_ENFORCEMENT = CatalogueEntry(
    id="REC_TRAFFIC_ENFORCEMENT",
    title="Increase roadside emissions enforcement",
    category=RecommendationCategory.ROAD_TRAFFIC,
    policy=Policy.TRAFFIC_MANAGEMENT,
    priority=Priority.ROUTINE,
    action=(
        "Deploy PUC (Pollution Under Control) checking teams to arterial routes in "
        "the affected zone during the identified peak window."
    ),
    rationale=(
        "Targets non-compliant vehicles, which are a disproportionate share of "
        "vehicular emissions. Defensible as routine enforcement regardless of the "
        "episode, which is why it is priced as ROUTINE rather than urgent."
    ),
    applicable_conditions=(
        "Moderate traffic evidence AND the hour falls in a commute peak. Both are "
        "required: the NO2/SO2 ratio alone is a weak discriminator (LR 2.11)."
    ),
    confidence_note=(
        "The traffic hypothesis is only weakly identified. Calibration against the "
        "COVID lockdown measured a likelihood ratio of 2.11 — 'weak' on the Kass & "
        "Raftery scale. This recommendation leans on that evidence; it does not "
        "rest on it. Enforcement is defensible on its own merits."
    ),
    limitations=[
        "Traffic evidence has no signal exogenous to the monitor. The COVID "
        "calibration also captured construction and industry stopping, so the "
        "likelihood ratio is an upper bound on the traffic-only effect.",
        "Road density is not yet ingested, so the spatial term is unavailable.",
    ],
    references=["Vayu Console COVID lockdown stress test (NO2 -54.4%, SO2 -3.7%)."],
)

TRAFFIC_COORDINATION = CatalogueEntry(
    id="REC_TRAFFIC_COORDINATION",
    title="Coordinate with traffic police on congestion management",
    category=RecommendationCategory.ROAD_TRAFFIC,
    policy=Policy.TRAFFIC_MANAGEMENT,
    priority=Priority.ROUTINE,
    action=(
        "Notify traffic police of the elevated window and request signal timing "
        "and diversion measures to reduce idling on affected corridors."
    ),
    rationale=(
        "Idling vehicles emit without moving anyone. Reducing congestion reduces "
        "emissions per journey, and is defensible independent of the attribution."
    ),
    applicable_conditions="Moderate traffic evidence AND a commute peak hour.",
    confidence_note=(
        "Supported by weak traffic evidence (LR 2.11). Defensible primarily as "
        "congestion management, which is worthwhile irrespective of this episode."
    ),
    limitations=["The system cannot estimate the emissions reduction achieved."],
    references=[],
)

# --------------------------------------------------------------------------
# INDUSTRIAL_MONITORING
# --------------------------------------------------------------------------
#
# Deliberately monitoring, never inspection or restriction. Phase 2 established
# the industrial hypothesis as very weakly identified: no natural experiment
# isolates it, so the module carries no likelihood ratio, and SO2 exists at only
# 36 of 96 stations. Sending inspectors to a plant on that basis is not something
# an officer could defend, and the plant's operator would be right to object.

INDUSTRIAL_REVIEW = CatalogueEntry(
    id="REC_INDUSTRIAL_REVIEW",
    title="Review SO2 readings against upwind point sources",
    category=RecommendationCategory.INDUSTRIAL_MONITORING,
    policy=Policy.MONITORING,
    priority=Priority.INFORMATIONAL,
    action=(
        "Flag the elevated SO2 reading for analyst review against known upwind "
        "point sources. Do not dispatch inspection on this basis alone."
    ),
    rationale=(
        "An elevated SO2 reading is worth a human look. It is not worth an "
        "enforcement action, because we cannot attribute it to a specific source."
    ),
    applicable_conditions="SO2 elevated relative to the Delhi median, with SO2 actually measured.",
    confidence_note=(
        "The industrial hypothesis is very weakly identified and carries NO "
        "likelihood ratio: no natural experiment isolates industry from traffic or "
        "construction. This is a prompt for human review, not a finding."
    ),
    limitations=[
        "SO2 is measured at only 36 of 96 Delhi stations. Absence of an SO2 sensor "
        "is not absence of industrial influence.",
        "Industrial and power-plant proximity are not ingested, so we cannot check "
        "whether a plausible source lies upwind.",
    ],
    references=[],
)

# --------------------------------------------------------------------------

CATALOGUE: dict[str, CatalogueEntry] = {
    entry.id: entry
    for entry in (
        SPRINKLERS,
        PUBLIC_ADVISORY,
        INCREASE_MONITORING,
        TRAFFIC_ENFORCEMENT,
        TRAFFIC_COORDINATION,
        INDUSTRIAL_REVIEW,
    )
}

#: Categories with no entries, and why. Exposed so the gap is visible rather than
#: looking like an oversight.
EMPTY_CATEGORIES: dict[str, str] = {
    RecommendationCategory.CONSTRUCTION.value: (
        "No construction evidence module exists. Phase 2 restricted the hypotheses "
        "to biomass, traffic and industrial, so any construction recommendation "
        "would be advice with no evidence behind it."
    ),
}
