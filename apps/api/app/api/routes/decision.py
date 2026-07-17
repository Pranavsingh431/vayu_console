"""Officer Decision Engine endpoints. Read-only."""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.decision import ENGINE_VERSION, DecisionEngine, explain
from app.decision.recommendations import CATALOGUE, EMPTY_CATEGORIES
from app.decision.schemas.decision import DecisionReport, Policy
from app.evidence.schemas.evidence import EvidenceReport

router = APIRouter(prefix="/decision", tags=["decision"])


class PolicyInfo(BaseModel):
    """A policy family and what it means operationally."""

    name: str
    description: str


class RecommendationInfo(BaseModel):
    """A catalogue entry, before any evidence is attached."""

    id: str
    title: str
    category: str
    policy: str
    priority: str
    action: str
    applicable_conditions: str
    confidence_note: str
    limitations: list[str]
    references: list[str]


_POLICY_DESCRIPTIONS: dict[str, str] = {
    Policy.EMERGENCY_RESPONSE.value: (
        "Commit operational resources now. Reserved for strong evidence from a "
        "hypothesis with a signal exogenous to the monitor — in practice, biomass."
    ),
    Policy.PUBLIC_HEALTH.value: (
        "Inform residents. Rests on the measured concentration rather than an "
        "inferred source, which is why it survives weak or contested attribution."
    ),
    Policy.TRAFFIC_MANAGEMENT.value: (
        "Coordinate enforcement and congestion measures. Priced ROUTINE because the "
        "traffic hypothesis is only weakly identified (LR 2.11)."
    ),
    Policy.MONITORING.value: (
        "Observe more closely. Always defensible: it commits nothing beyond "
        "attention and is the correct response to uncertainty."
    ),
    Policy.NO_ACTION.value: (
        "Take no action. Distinct from insufficient evidence — this means we looked "
        "and nothing warrants intervention."
    ),
}


@router.get("/policies", response_model=list[PolicyInfo], summary="Policy families")
async def decision_policies() -> list[PolicyInfo]:
    """List the policy families rules can map evidence onto."""
    return [PolicyInfo(name=p.value, description=_POLICY_DESCRIPTIONS[p.value]) for p in Policy]


@router.get(
    "/recommendations",
    response_model=list[RecommendationInfo],
    summary="The recommendation catalogue",
)
async def decision_recommendations() -> list[RecommendationInfo]:
    """List every recommendation the engine can ever emit.

    Deliberately short. Each entry had to pass one test: could a pollution control
    officer defend this in a meeting? `GET /decision/gaps` lists what was excluded
    and why.
    """
    return [
        RecommendationInfo(
            id=e.id,
            title=e.title,
            category=e.category.value,
            policy=e.policy.value,
            priority=e.priority.value,
            action=e.action,
            applicable_conditions=e.applicable_conditions,
            confidence_note=e.confidence_note,
            limitations=e.limitations,
            references=e.references,
        )
        for e in CATALOGUE.values()
    ]


@router.get("/gaps", summary="Categories with no recommendations, and why")
async def decision_gaps() -> dict[str, object]:
    """Explain what the engine deliberately will not recommend.

    Exposed so the absence reads as a decision rather than an oversight.
    """
    return {
        "empty_categories": EMPTY_CATEGORIES,
        "note": (
            "A category with no entries means we have no evidence module capable of "
            "supporting advice in it. Recommending anyway would be advice with "
            "nothing behind it."
        ),
    }


@router.get("/rules", summary="The rules, and why each is defensible")
async def decision_rules() -> dict[str, object]:
    """List every rule with its justification and its declared scope limits."""
    engine = DecisionEngine()
    return {
        "engine_version": ENGINE_VERSION,
        "note": (
            "Rules fire on the presence of evidence, never its absence. Weak fire "
            "evidence can mean the satellite did not pass over, so it never implies "
            "another source."
        ),
        "rules": [
            {
                "id": r.id,
                "description": r.description,
                "defensible_because": r.defensible_because,
                "policy": r.policy.value,
                "recommendations": list(r.recommendation_ids),
                "does_not_imply": r.does_not_imply,
            }
            for r in engine.rule_engine.rules
        ],
    }


@router.post(
    "/evaluate",
    response_model=DecisionReport,
    summary="Turn an Evidence Report into a Decision Report",
)
async def decision_evaluate(report: EvidenceReport) -> DecisionReport:
    """Produce recommendations from evidence.

    Consumes an Evidence Report only — the engine never touches raw data, which is
    what guarantees every recommendation traces back to observed evidence.
    """
    return DecisionEngine().evaluate(report)


@router.get("/example", response_model=DecisionReport, summary="A worked Decision Report")
async def decision_example() -> DecisionReport:
    """Diwali 2019 at Anand Vihar, end to end.

    Builds the evidence from the Evidence Engine's own example, so the two
    endpoints cannot drift apart.
    """
    from app.api.routes.evidence import _example_context
    from app.evidence import EvidenceAggregator

    return DecisionEngine().evaluate(EvidenceAggregator().evaluate(_example_context()))


@router.get("/example/explain", summary="Why this recommendation? (Challenge feature)")
async def decision_example_explain() -> list[dict[str, object]]:
    """Explain every recommendation in the example report.

    Powers the UI's "Challenge Recommendation" affordance: supporting evidence,
    contradicting evidence, assumptions, and how to argue against it.
    """
    from app.api.routes.evidence import _example_context
    from app.evidence import EvidenceAggregator

    report = DecisionEngine().evaluate(EvidenceAggregator().evaluate(_example_context()))
    return [explain(r) for r in report.recommendations]
