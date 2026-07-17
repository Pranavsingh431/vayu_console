"""The Officer Decision Engine.

Consumes Evidence Reports and produces transparent, deterministic, defensible
recommendations. No model, no language model, no probabilities.

The governing test for every rule and every catalogue entry: could a pollution
control officer defend this in a meeting? See docs/architecture/decision-engine.md.
"""

from app.decision.engine.service import ENGINE_VERSION, DecisionEngine, explain
from app.decision.rules.rules import ALL_RULES, Rule, RuleEngine

__all__ = ["ALL_RULES", "ENGINE_VERSION", "DecisionEngine", "Rule", "RuleEngine", "explain"]
