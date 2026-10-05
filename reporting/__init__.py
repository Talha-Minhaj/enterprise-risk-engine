"""
Reporting Package
=================
Automated portfolio reporting, executive multi-sheet Excel generation,
and interactive visualization charts for the Enterprise Risk System.
"""

from .reports import generate_excel_risk_report, generate_executive_text_summary
from .visualizer import (
    plot_risk_tier_distribution,
    plot_exposure_vs_risk,
    plot_sector_risk_breakdown,
    plot_entity_spider_radar,
)

__all__ = [
    "generate_excel_risk_report",
    "generate_executive_text_summary",
    "plot_risk_tier_distribution",
    "plot_exposure_vs_risk",
    "plot_sector_risk_breakdown",
    "plot_entity_spider_radar",
]
