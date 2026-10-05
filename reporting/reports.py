"""
reports.py
==========
Executive portfolio summary reporting, automated multi-tab Excel export,
and risk watchlist generation.
"""

import io
import pandas as pd
from typing import Dict, Any, List

from risk_engine.mitigation import generate_mitigation_actions, generate_portfolio_decision_summary


def generate_excel_risk_report(df_scored: pd.DataFrame) -> bytes:
    """
    Generates an executive-ready multi-sheet Excel workbook in memory containing:
      1. Executive Overview & KPIs
      2. High-Risk Watchlist
      3. Full Scored Portfolio
      4. Prescriptive Action Plan
    """
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        # Sheet 1: Executive KPI Metrics
        summary = generate_portfolio_decision_summary(df_scored)
        kpi_data = [
            {"Metric": "Total Portfolio Counterparties", "Value": f"{summary['total_entities']:,}"},
            {"Metric": "Total Portfolio Exposure (USD)", "Value": f"${summary['total_exposure_usd']:,.2f}"},
            {"Metric": "Total Expected Loss (USD)", "Value": f"${summary['total_expected_loss_usd']:,.2f}"},
            {"Metric": "Portfolio Expected Loss Rate (%)", "Value": f"{summary['portfolio_loss_rate_pct']:.2f}%"},
            {"Metric": "Average Composite Risk Score (0-100)", "Value": f"{summary['average_composite_score']:.1f}"},
            {"Metric": "High-Risk Entity Count", "Value": f"{summary['high_risk_count']:,} ({summary['high_risk_percentage']:.1f}%)"},
            {"Metric": "Exposure at High Risk (USD)", "Value": f"${summary['high_risk_exposure_usd']:,.2f}"},
        ]
        df_kpi = pd.DataFrame(kpi_data)
        df_kpi.to_excel(writer, sheet_name="Executive KPIs", index=False)

        # Sheet 2: High-Risk Watchlist
        df_watchlist = df_scored[df_scored["risk_tier"] == "High Risk"].sort_values(
            by="composite_risk_score", ascending=False
        )
        cols_watch = [
            "entity_id", "entity_name", "sector", "jurisdiction", "credit_rating",
            "total_exposure_usd", "expected_loss_usd", "composite_risk_score",
            "credit_risk_score", "financial_risk_score", "operational_risk_score"
        ]
        available_watch_cols = [c for c in cols_watch if c in df_watchlist.columns]
        df_watchlist[available_watch_cols].to_excel(writer, sheet_name="High-Risk Watchlist", index=False)

        # Sheet 3: Full Scored Portfolio
        df_scored.to_excel(writer, sheet_name="Portfolio Scoring Register", index=False)

        # Sheet 4: Prescriptive Action Plan for Top High Risk Entities
        top_risky = df_watchlist.head(25)
        mitigation_rows = []
        for _, row in top_risky.iterrows():
            actions = generate_mitigation_actions(row)
            for act in actions:
                mitigation_rows.append({
                    "Entity ID": row.get("entity_id"),
                    "Entity Name": row.get("entity_name"),
                    "Risk Tier": row.get("risk_tier"),
                    "Composite ERS": row.get("composite_risk_score"),
                    "Risk Category": act["category"],
                    "Trigger Violation": act["trigger"],
                    "Mitigation Action": act["action"],
                    "Priority": act["priority"],
                    "Timeline": act["timeframe"],
                    "Expected Impact": act["expected_impact"]
                })
        df_mitigation = pd.DataFrame(mitigation_rows)
        df_mitigation.to_excel(writer, sheet_name="Prescriptive Action Plan", index=False)

    return output.getvalue()


def generate_executive_text_summary(df_scored: pd.DataFrame) -> str:
    """
    Generates a concise markdown executive briefing of portfolio risk metrics.
    """
    summary = generate_portfolio_decision_summary(df_scored)
    
    text = f"""
================================================================================
ENTERPRISE RISK ASSESSMENT & DECISION SUPPORT SYSTEM: EXECUTIVE SUMMARY
================================================================================
Portfolio Scope: {summary['total_entities']} Counterparties across 8 Global Sectors
Total Exposure at Default (EAD): ${summary['total_exposure_usd']:,.2f}
Total Expected Loss (EL):        ${summary['total_expected_loss_usd']:,.2f} ({summary['portfolio_loss_rate_pct']:.2f}% loss rate)
Portfolio Mean Composite Score:  {summary['average_composite_score']:.1f} / 100

Risk Tier Breakdown:
  - Low Risk:    {summary['tier_distribution_counts'].get('Low Risk', 0):>4} entities | Exposure: ${summary['tier_distribution_exposure_usd'].get('Low Risk', 0.0):,.2f}
  - Medium Risk: {summary['tier_distribution_counts'].get('Medium Risk', 0):>4} entities | Exposure: ${summary['tier_distribution_exposure_usd'].get('Medium Risk', 0.0):,.2f}
  - High Risk:   {summary['tier_distribution_counts'].get('High Risk', 0):>4} entities | Exposure: ${summary['tier_distribution_exposure_usd'].get('High Risk', 0.0):,.2f}

Priority Watchlist (Top 5 Vulnerabilities):
"""
    for idx, ent in enumerate(summary["top_watchlist_entities"][:5], 1):
        text += (
            f"  {idx}. [{ent['entity_id']}] {ent['entity_name']} ({ent['sector']}) "
            f"- Rating: {ent['credit_rating']} | Score: {ent['composite_risk_score']:.1f}/100 "
            f"| EAD: ${ent['total_exposure_usd']:,.0f}\n"
        )
    text += "================================================================================"
    return text
