"""The Evidence Engine's contract.

Everything in `app/evidence` composes on these types. They encode the conclusions
of the Phase 2 research spike (docs/research/inference.md), and the constraints
are deliberate:

* There is no probability anywhere. `P(source | features)` is not estimable from
  our data; anything shaped like a probability would be fabricated. See §1-§4.
* Strengths do not sum to 1 and must never be normalised. They are strengths of
  evidence for independent hypotheses, not shares of a pie. A softmax anywhere
  in this package reintroduces source apportionment through the back door.
* `INSUFFICIENT_EVIDENCE` is a first-class outcome, not an error. A module that
  cannot see is required to say so rather than guess.
"""

from __future__ import annotations

import datetime as dt
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class Hypothesis(StrEnum):
    """The competing explanations the engine reasons about.

    Not mutually exclusive: on a Diwali night during stubble season, biomass and
    traffic evidence are both legitimately present.
    """

    BIOMASS = "biomass"
    TRAFFIC = "traffic"
    INDUSTRIAL = "industrial"


class EvidenceStrength(StrEnum):
    """How strongly the observations favour a hypothesis.

    Bands follow Kass & Raftery (1995) for interpreting a likelihood ratio, so a
    label carries a citation rather than a taste. `INSUFFICIENT_EVIDENCE` is
    distinct from `VERY_WEAK`: the first means we cannot see, the second means we
    looked and found little.
    """

    INSUFFICIENT_EVIDENCE = "insufficient_evidence"
    VERY_WEAK = "very_weak"
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


class EvidenceQuality(StrEnum):
    """How much the underlying data can bear.

    Deliberately orthogonal to strength. Strong evidence resting on poor data is
    a real and important state: one station reporting, a stale satellite pass, a
    sensor with 40% uptime. Collapsing the two would hide exactly the cases an
    officer most needs flagged.
    """

    NO_DATA = "no_data"
    POOR = "poor"
    FAIR = "fair"
    GOOD = "good"
    HIGH = "high"


class ValidationStatus(StrEnum):
    """Whether a module has survived falsification against a natural experiment.

    `REJECTED` means the module is deleted from the product (inference.md §5.7).
    It exists here so a rejection can be reported before removal, and so the
    aggregator can refuse to serve a rejected module's output.
    """

    ACCEPTED = "accepted"
    REJECTED = "rejected"
    UNCERTAIN = "uncertain"
    PENDING = "pending"


class Identification(StrEnum):
    """How well the hypothesis is identified by the data we hold.

    From inference.md §5.6. This is a property of the *design*, not of any single
    reading: biomass has a signal exogenous to the monitor (satellites do not read
    our sensors), traffic does not, industrial barely exists.
    """

    STRONG = "strong"
    WEAK = "weak"
    VERY_WEAK = "very_weak"
    UNIDENTIFIED = "unidentified"


# Kass & Raftery bands over a likelihood ratio. A module that computes an LR maps
# it through here rather than inventing its own scale.
_LR_BANDS: tuple[tuple[float, EvidenceStrength], ...] = (
    (3.0, EvidenceStrength.VERY_WEAK),
    (10.0, EvidenceStrength.WEAK),
    (30.0, EvidenceStrength.MODERATE),
    (100.0, EvidenceStrength.STRONG),
    (float("inf"), EvidenceStrength.VERY_STRONG),
)

STRENGTH_STARS: dict[EvidenceStrength, str] = {
    EvidenceStrength.INSUFFICIENT_EVIDENCE: "—",
    EvidenceStrength.VERY_WEAK: "★",
    EvidenceStrength.WEAK: "★★",
    EvidenceStrength.MODERATE: "★★★",
    EvidenceStrength.STRONG: "★★★★",
    EvidenceStrength.VERY_STRONG: "★★★★★",
}

STRENGTH_EXPLANATION: dict[EvidenceStrength, str] = {
    EvidenceStrength.INSUFFICIENT_EVIDENCE: (
        "The observations needed to judge this hypothesis are missing. This is not "
        "evidence against it — we cannot see."
    ),
    EvidenceStrength.VERY_WEAK: "Observations barely favour this hypothesis over its absence.",
    EvidenceStrength.WEAK: "Observations lean towards this hypothesis but are far from decisive.",
    EvidenceStrength.MODERATE: "Observations substantially favour this hypothesis.",
    EvidenceStrength.STRONG: "Observations strongly favour this hypothesis.",
    EvidenceStrength.VERY_STRONG: (
        "Observations decisively favour this hypothesis over its absence. This is still "
        "evidence, not a measurement of contribution."
    ),
}


def strength_from_likelihood_ratio(lr: float) -> EvidenceStrength:
    """Map a likelihood ratio onto a Kass & Raftery band.

    An LR below 1 favours the hypothesis' *absence*; it is folded so that the band
    describes the strength of evidence in whichever direction it points. Callers
    must communicate direction themselves — a strength label alone never implies
    the hypothesis is true.
    """
    if lr <= 0:
        return EvidenceStrength.INSUFFICIENT_EVIDENCE
    folded = max(lr, 1.0 / lr)
    for upper, strength in _LR_BANDS:
        if folded < upper:
            return strength
    return EvidenceStrength.VERY_STRONG


class Observation(BaseModel):
    """One observed fact, traceable to stored data.

    Every field an officer might question must be answerable from here: what was
    measured, when, from which source. An observation with no source is not
    evidence, it is an assertion.
    """

    model_config = ConfigDict(frozen=True)

    label: str = Field(description="Human-readable statement of the fact.")
    value: float | str | None = Field(default=None, description="The measured value.")
    unit: str | None = None
    source: str = Field(
        description="Which dataset this came from, e.g. openaq_s3, firms_viirs_snpp_sp."
    )
    observed_at: dt.datetime | None = Field(
        default=None, description="When the fact was observed (UTC), not when we computed it."
    )


class HistoricalValidation(BaseModel):
    """The outcome of a falsification test against a natural experiment.

    `detail` must state what the test would have had to show to fail. A test that
    could not have failed is ceremonial and does not belong here.
    """

    model_config = ConfigDict(frozen=True)

    experiment: str = Field(description="e.g. 'COVID lockdown 2020'.")
    status: ValidationStatus
    detail: str = Field(description="What was measured, and what would have rejected the module.")
    likelihood_ratio: float | None = None


class EvidenceResult(BaseModel):
    """One module's verdict on one hypothesis, at one station and time.

    This is the unit the whole engine trades in. It is deliberately verbose:
    an officer must be able to reconstruct the reasoning without reading code.
    """

    model_config = ConfigDict(use_enum_values=True)

    name: str = Field(description="Module name, e.g. 'biomass'.")
    hypothesis: Hypothesis
    status: EvidenceStrength = Field(description="Alias of strength, kept for the module contract.")
    strength: EvidenceStrength
    evidence_quality: EvidenceQuality
    identification: Identification

    stars: str = Field(description="Kass & Raftery band as stars, for display.")
    explanation: str = Field(description="What this strength level means.")
    likelihood_ratio: float | None = Field(
        default=None, description="Where the module computes one. Absent is honest, not a gap."
    )

    supporting_observations: list[Observation] = Field(default_factory=list)
    # Never optional. A module that reports only what agrees with it is advocacy,
    # not evidence — this is the field that makes the engine a differential diagnosis.
    contradicting_observations: list[Observation] = Field(default_factory=list)

    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    historical_validation: list[HistoricalValidation] = Field(default_factory=list)
    references: list[str] = Field(default_factory=list)

    @property
    def is_insufficient(self) -> bool:
        return self.strength == EvidenceStrength.INSUFFICIENT_EVIDENCE


class EvidenceReport(BaseModel):
    """The aggregator's output: every hypothesis, side by side, unranked by probability."""

    model_config = ConfigDict(use_enum_values=True)

    station: str
    station_id: int | None = None
    evaluated_at: dt.datetime = Field(description="The instant being explained (UTC).")
    # The measured concentration at this station-hour. Not evidence for any
    # hypothesis — it is the thing the hypotheses are competing to explain, and
    # the officer's headline. Absent when the station did not report PM2.5.
    measured_pm25: float | None = Field(
        default=None, description="Measured PM2.5 (µg/m³). The observed fact, not an inference."
    )
    generated_at: dt.datetime = Field(description="When this report was produced (UTC).")

    evidence: list[EvidenceResult]
    summary: str

    overall_quality: EvidenceQuality
    assumptions: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)

    # Provenance, per the Phase 2 traceability requirement.
    engine_version: str
    data_sources: list[str] = Field(default_factory=list)

    @property
    def notice(self) -> str:
        return (
            "This report presents evidence for competing hypotheses. It does not "
            "measure source contributions and the strengths do not sum to 100%. "
            "See docs/research/scientific-limitations.md §1."
        )
