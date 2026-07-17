"""The Evidence Engine.

Produces evidence for competing hypotheses. It does not classify pollution
sources, does not output probabilities, and does not normalise strengths — see
docs/architecture/evidence-engine.md and docs/research/inference.md.
"""

from app.evidence.aggregator.service import ENGINE_VERSION, EvidenceAggregator, default_modules
from app.evidence.base import EvidenceContext, EvidenceModule, FireObservation

__all__ = [
    "ENGINE_VERSION",
    "EvidenceAggregator",
    "EvidenceContext",
    "EvidenceModule",
    "FireObservation",
    "default_modules",
]
