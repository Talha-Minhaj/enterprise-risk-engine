"""
Risk Engine Package
===================
Quantitative multi-factor risk scoring, classification tiers,
threshold tripwires, and actionable decision support mitigation logic.
"""

from .config import RiskEngineConfig, DEFAULT_CONFIG
from .scoring import calculate_risk_scores, score_single_entity
from .mitigation import generate_mitigation_actions, generate_portfolio_decision_summary
from .consulting_suite import generate_consulting_suite

__all__ = [
    "RiskEngineConfig",
    "DEFAULT_CONFIG",
    "calculate_risk_scores",
    "score_single_entity",
    "generate_mitigation_actions",
    "generate_portfolio_decision_summary",
    "generate_consulting_suite",
]
