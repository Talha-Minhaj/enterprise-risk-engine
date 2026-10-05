"""
consulting_engine.py
====================
Backward-compatible proxy module for the Enterprise Risk & Consulting Decision Engine.
Delegates to the modular risk_engine.consulting_suite package.
"""

from risk_engine.consulting_suite import (
    RiskItem,
    RaciItem,
    GapAnalysisItem,
    ConsultingSuiteOutput,
    generate_consulting_suite,
)

__all__ = [
    "RiskItem",
    "RaciItem",
    "GapAnalysisItem",
    "ConsultingSuiteOutput",
    "generate_consulting_suite",
]
