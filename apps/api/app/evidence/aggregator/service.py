"""Evidence aggregation.

Combines independent module verdicts into one report. Deliberately does very
little: it does not rank by probability, does not normalise, and does not decide
which hypothesis is "the answer". Those are all ways of quietly reintroducing
source apportionment.

Ordering is by evidence strength for display only. Two hypotheses may both be
strong — on a Diwali night in stubble season, that is the correct answer.
"""

from __future__ import annotations

import datetime as dt
import logging

from app.evidence.base import EvidenceContext, EvidenceModule
from app.evidence.biomass.module import BiomassEvidenceModule
from app.evidence.industrial.module import IndustrialEvidenceModule
from app.evidence.schemas.evidence import (
    STRENGTH_STARS,
    EvidenceQuality,
    EvidenceReport,
    EvidenceResult,
    EvidenceStrength,
    hypothesis_prose,
)
from app.evidence.traffic.module import TrafficEvidenceModule

logger = logging.getLogger(__name__)

ENGINE_VERSION = "0.1.0"

_STRENGTH_RANK: dict[str, int] = {
    EvidenceStrength.INSUFFICIENT_EVIDENCE.value: -1,
    EvidenceStrength.VERY_WEAK.value: 0,
    EvidenceStrength.WEAK.value: 1,
    EvidenceStrength.MODERATE.value: 2,
    EvidenceStrength.STRONG.value: 3,
    EvidenceStrength.VERY_STRONG.value: 4,
}

_QUALITY_RANK: dict[str, int] = {
    EvidenceQuality.NO_DATA.value: 0,
    EvidenceQuality.POOR.value: 1,
    EvidenceQuality.FAIR.value: 2,
    EvidenceQuality.GOOD.value: 3,
    EvidenceQuality.HIGH.value: 4,
}
_RANK_QUALITY = {v: k for k, v in _QUALITY_RANK.items()}


def default_modules() -> list[EvidenceModule]:
    """The registered modules.

    Adding a hypothesis in a later phase means implementing `EvidenceModule` and
    appending here — the aggregator itself does not change.
    """
    return [
        BiomassEvidenceModule(),
        TrafficEvidenceModule(),
        IndustrialEvidenceModule(),
    ]


class EvidenceAggregator:
    """Runs every module and assembles the report."""

    def __init__(self, modules: list[EvidenceModule] | None = None) -> None:
        self._modules = modules if modules is not None else default_modules()

    @property
    def modules(self) -> list[EvidenceModule]:
        return list(self._modules)

    def evaluate(self, context: EvidenceContext) -> EvidenceReport:
        results: list[EvidenceResult] = []
        for module in self._modules:
            try:
                results.append(module.evaluate(context))
            except Exception as exc:
                # One broken module must not cost the officer the evidence that
                # other modules did produce. Report it as insufficient and carry on.
                #
                # `module` is a reserved LogRecord attribute — passing it via extra
                # raises inside logging itself, which would crash the very handler
                # meant to contain the failure.
                logger.exception("evidence module failed", extra={"evidence_module": module.name})
                results.append(
                    module.insufficient(
                        f"The {module.name} module failed to evaluate: {type(exc).__name__}. "
                        "This is a defect, not a finding about the hypothesis."
                    )
                )

        # Display order only. Not a ranking of contribution.
        results.sort(key=lambda r: _STRENGTH_RANK.get(str(r.strength), -1), reverse=True)

        # Negative values are sentinels; `has` already excludes them.
        pm25 = context.pollutants.get("pm25")
        return EvidenceReport(
            station=context.station_name,
            station_id=context.station_id,
            evaluated_at=context.evaluated_at,
            measured_pm25=pm25 if pm25 is not None and pm25 >= 0 else None,
            generated_at=dt.datetime.now(dt.UTC),
            evidence=results,
            summary=self._summarise(results),
            overall_quality=self._overall_quality(results),
            assumptions=_dedupe(a for r in results for a in r.assumptions),
            limitations=_dedupe(limit for r in results for limit in r.limitations),
            engine_version=ENGINE_VERSION,
            data_sources=_dedupe(
                o.source
                for r in results
                for o in (*r.supporting_observations, *r.contradicting_observations)
            ),
        )

    @staticmethod
    def _summarise(results: list[EvidenceResult]) -> str:
        """A sentence an officer can read, phrased as evidence not attribution."""
        judged = [
            r for r in results if str(r.strength) != EvidenceStrength.INSUFFICIENT_EVIDENCE.value
        ]
        if not judged:
            return (
                "No hypothesis could be judged at this station-hour: the required "
                "observations are missing. This is not evidence that the air is clean."
            )

        parts = [
            f"{hypothesis_prose(r.hypothesis)} "
            f"{STRENGTH_STARS.get(EvidenceStrength(str(r.strength)), '')}".strip()
            for r in judged
        ]
        blind = [
            hypothesis_prose(r.hypothesis)
            for r in results
            if str(r.strength) == EvidenceStrength.INSUFFICIENT_EVIDENCE.value
        ]
        sentence = "Evidence: " + "; ".join(parts) + "."
        if blind:
            sentence += (
                f" Could not judge: {', '.join(blind)} — required "
                "observations unavailable, which is not evidence of absence."
            )
        return sentence

    @staticmethod
    def _overall_quality(results: list[EvidenceResult]) -> EvidenceQuality:
        """The worst quality among modules that reached a verdict.

        Deliberately pessimistic: a report is only as trustworthy as its weakest
        judged component, and averaging would let one good module mask a blind one.
        """
        judged = [
            r for r in results if str(r.strength) != EvidenceStrength.INSUFFICIENT_EVIDENCE.value
        ]
        if not judged:
            return EvidenceQuality.NO_DATA
        worst = min(_QUALITY_RANK.get(str(r.evidence_quality), 0) for r in judged)
        return EvidenceQuality(_RANK_QUALITY[worst])


def _dedupe(items) -> list[str]:  # type: ignore[no-untyped-def]
    """Order-preserving dedupe."""
    seen: dict[str, None] = {}
    for item in items:
        if item:
            seen.setdefault(str(item), None)
    return list(seen)
