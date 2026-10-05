"""
mitigation.py
=============
Automated decision support and prescriptive risk mitigation logic.
Evaluates risk tripwires across credit, liquidity, and operational metrics
to generate prioritized corporate intervention plans and executive briefs.
"""

import os
from typing import List, Dict, Any, Optional
import pandas as pd
from pydantic import BaseModel, Field

from .config import RiskEngineConfig, DEFAULT_CONFIG


class MitigationAction(BaseModel):
    """Structured decision support recommendation for an identified risk tripwire."""
    category: str = Field(description="Risk category: Counterparty, Liquidity, Operational, or Governance")
    trigger: str = Field(description="Underlying metric or threshold violation")
    action: str = Field(description="Concrete executive mitigation action")
    priority: str = Field(description="Urgency: Critical, High, Medium, or Advisory")
    timeframe: str = Field(description="Recommended execution timeline")
    expected_impact: str = Field(description="Anticipated risk exposure reduction")


def generate_mitigation_actions(
    entity_row: pd.Series,
    config: Optional[RiskEngineConfig] = None
) -> List[Dict[str, str]]:
    """
    Evaluates tripwires for a specific entity and returns a prioritized list of mitigation actions.
    """
    cfg = config or DEFAULT_CONFIG
    actions: List[MitigationAction] = []

    # 1. Counterparty Credit Tripwires
    pd_val = float(entity_row.get("probability_of_default", 0.0))
    credit_score = float(entity_row.get("credit_risk_score", 0.0))
    de_val = float(entity_row.get("debt_to_equity", 0.0))
    exposure = float(entity_row.get("total_exposure_usd", 0.0))

    if pd_val >= cfg.crit_probability_of_default or credit_score >= 70.0:
        actions.append(MitigationAction(
            category="Counterparty Credit",
            trigger=f"Elevated Probability of Default ({pd_val:.2%}) & Credit Risk Score ({credit_score:.1f}/100)",
            action="Require cash collateralization, irrevocable Standby Letter of Credit (SBLC), or third-party corporate parent guarantee.",
            priority="Critical",
            timeframe="Immediate (0-15 Days)",
            expected_impact=f"Protects ${(exposure * 0.75):,.0f} in potential default exposure."
        ))

    if de_val >= cfg.crit_debt_to_equity:
        actions.append(MitigationAction(
            category="Leverage / Solvency",
            trigger=f"Excessive Debt-to-Equity Ratio ({de_val:.2f}x vs {cfg.crit_debt_to_equity}x threshold)",
            action="Compress standard commercial payment terms (shift from Net 60 to Net 15 or Milestone Advance Billing) and establish strict credit ceiling.",
            priority="High",
            timeframe="Within 30 Days",
            expected_impact="Reduces working capital exposure duration by 45 days."
        ))

    # 2. Financial & Liquidity Distress Tripwires
    cr_val = float(entity_row.get("current_ratio", 2.0))
    icr_val = float(entity_row.get("interest_coverage_ratio", 5.0))
    fin_score = float(entity_row.get("financial_risk_score", 0.0))

    if cr_val < cfg.crit_current_ratio or fin_score >= 65.0:
        actions.append(MitigationAction(
            category="Liquidity Health",
            trigger=f"Deficient Current Ratio ({cr_val:.2f}x < 1.0x buffer) and high financial distress score ({fin_score:.1f}/100)",
            action="Mandate weekly cash-flow verification, senior security liens on receivables, and establish escrow account for upcoming project deliverables.",
            priority="Critical",
            timeframe="Immediate (7-14 Days)",
            expected_impact="Ensures ring-fenced funds for operational fulfillment."
        ))

    if icr_val < cfg.crit_interest_coverage:
        actions.append(MitigationAction(
            category="Debt Servicing",
            trigger=f"Constrained Interest Coverage Ratio ({icr_val:.2f}x < {cfg.crit_interest_coverage}x target)",
            action="Enforce negative pledge covenants and initiate monthly debt service compliance certification.",
            priority="Medium",
            timeframe="Within 45 Days",
            expected_impact="Provides early warning radar 60 days before potential restructuring."
        ))

    # 3. Operational & Governance Tripwires
    ctrl_val = float(entity_row.get("control_effectiveness_score", 80.0))
    audit_findings = int(entity_row.get("audit_findings_count", 0))
    ops_score = float(entity_row.get("operational_risk_score", 0.0))
    sla_rate = float(entity_row.get("sla_breach_rate", 0.0))

    if ctrl_val < cfg.crit_control_effectiveness or ops_score >= 65.0:
        actions.append(MitigationAction(
            category="Operational Controls",
            trigger=f"Substandard Internal Control Effectiveness ({ctrl_val:.1f}%) and high operational risk ({ops_score:.1f}/100)",
            action="Commission independent remediation audit, implement automated dual-authorization workflows, and institute active performance oversight.",
            priority="High",
            timeframe="Within 30 Days",
            expected_impact="Targets 40% improvement in internal control reliability."
        ))

    if audit_findings >= cfg.crit_audit_findings:
        actions.append(MitigationAction(
            category="Audit & Compliance",
            trigger=f"Unresolved Audit Findings Count ({audit_findings} findings >= {cfg.crit_audit_findings} tolerance)",
            action="Escalate findings to Enterprise Audit Committee; issue formal remediation ultimatum with financial withholding penalties.",
            priority="Critical",
            timeframe="Immediate (0-15 Days)",
            expected_impact="Eliminates statutory non-compliance exposure and contractual liabilities."
        ))

    if sla_rate >= 0.15:
        actions.append(MitigationAction(
            category="Operational SLA",
            trigger=f"Excessive SLA Breach Frequency ({sla_rate:.1%})",
            action="Enact contractual liquidated damages clauses and activate secondary dual-source vendor contingency protocol.",
            priority="Medium",
            timeframe="Within 30 Days",
            expected_impact="Mitigates single-point-of-failure supply or delivery disruption."
        ))

    # Fallback if no specific tripwire fired (clean entity)
    if not actions:
        actions.append(MitigationAction(
            category="Routine Governance",
            trigger="All metrics within standard tolerance thresholds",
            action="Maintain standard annual review cycle, routine automated KPI monitoring, and standard commercial credit lines.",
            priority="Advisory",
            timeframe="Annual Review",
            expected_impact="Continuous baseline monitoring with zero operational disruption."
        ))

    return [a.model_dump() for a in actions]


def generate_portfolio_decision_summary(df_scored: pd.DataFrame) -> Dict[str, Any]:
    """
    Synthesizes portfolio-level decision metrics, exposure concentrations,
    and high-risk watchlists for senior leadership.
    """
    total_exposure = float(df_scored["total_exposure_usd"].sum())
    total_expected_loss = float(df_scored["expected_loss_usd"].sum())
    
    tier_counts = df_scored["risk_tier"].value_counts().to_dict()
    tier_exposure = df_scored.groupby("risk_tier")["total_exposure_usd"].sum().to_dict()

    high_risk_df = df_scored[df_scored["risk_tier"] == "High Risk"].sort_values(
        by="composite_risk_score", ascending=False
    )

    summary = {
        "total_entities": len(df_scored),
        "total_exposure_usd": total_exposure,
        "total_expected_loss_usd": total_expected_loss,
        "portfolio_loss_rate_pct": (total_expected_loss / total_exposure * 100.0) if total_exposure > 0 else 0.0,
        "average_composite_score": float(df_scored["composite_risk_score"].mean()),
        "tier_distribution_counts": tier_counts,
        "tier_distribution_exposure_usd": tier_exposure,
        "high_risk_count": len(high_risk_df),
        "high_risk_exposure_usd": float(tier_exposure.get("High Risk", 0.0)),
        "high_risk_percentage": (len(high_risk_df) / len(df_scored) * 100.0) if len(df_scored) > 0 else 0.0,
        "top_watchlist_entities": high_risk_df[["entity_id", "entity_name", "sector", "credit_rating", "total_exposure_usd", "composite_risk_score"]].head(10).to_dict(orient="records")
    }

    return summary


def generate_ai_risk_brief(
    entity_data: Dict[str, Any],
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash"
) -> str:
    """
    Optional Generative AI advisory: synthesizes a natural language executive risk memo
    using Google Gemini API when an API key is available.
    """
    effective_api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not effective_api_key:
        return (
            "*(GenAI Executive Brief unavailable: Set GEMINI_API_KEY in .env or the sidebar "
            "to unlock automated qualitative risk memos.)*"
        )

    try:
        from google import genai
        client = genai.Client(api_key=effective_api_key)
        prompt = f"""
You are a Senior Risk & Financial Strategy Consultant. Synthesize a concise, 3-paragraph Executive Risk Briefing Memo for the Board of Directors regarding the following enterprise counterparty:

Entity ID: {entity_data.get('entity_id')}
Entity Name: {entity_data.get('entity_name')}
Sector: {entity_data.get('sector')}
Jurisdiction: {entity_data.get('jurisdiction')}
External Rating: {entity_data.get('credit_rating')}
Total Exposure: ${entity_data.get('total_exposure_usd', 0):,.2f}
Expected Loss: ${entity_data.get('expected_loss_usd', 0):,.2f}
Composite Enterprise Risk Score: {entity_data.get('composite_risk_score')}/100 ({entity_data.get('risk_tier')})

Detailed Breakdown:
- Credit Risk Score: {entity_data.get('credit_risk_score')}/100 (PD: {entity_data.get('probability_of_default', 0)*100:.2f}%, LGD: {entity_data.get('loss_given_default', 0)*100:.1f}%)
- Financial Distress Score: {entity_data.get('financial_risk_score')}/100 (Current Ratio: {entity_data.get('current_ratio')}, D/E: {entity_data.get('debt_to_equity')}, ICR: {entity_data.get('interest_coverage_ratio')})
- Operational Risk Score: {entity_data.get('operational_risk_score')}/100 (Control Score: {entity_data.get('control_effectiveness_score')}%, Audit Findings: {entity_data.get('audit_findings_count')}, SLA Breach: {entity_data.get('sla_breach_rate', 0)*100:.1f}%)

Format the response into:
1. Executive Risk Diagnostic
2. Primary Vulnerability Drivers
3. Prescriptive Strategic Recommendation
Keep it sharp, quantitative, and professional.
"""
        response = client.models.generate_content(
            model=model_name,
            contents=prompt
        )
        return response.text or "No text generated."
    except Exception as e:
        return f"*(Error querying Gemini AI: {str(e)})*"
