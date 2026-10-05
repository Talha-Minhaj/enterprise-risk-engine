"""
scoring.py
==========
Quantitative multi-factor risk scoring engine for enterprise portfolios.
Calculates Credit Risk, Financial & Liquidity Distress, Operational & Compliance Risk,
and composite Enterprise Risk Score (ERS) with classification tiers.
"""

import numpy as np
import pandas as pd
from typing import Dict, Any, Optional

from .config import RiskEngineConfig, DEFAULT_CONFIG


def calculate_risk_scores(
    df: pd.DataFrame,
    config: Optional[RiskEngineConfig] = None
) -> pd.DataFrame:
    """
    Executes a vectorized risk assessment across all entity records in the dataset.
    Appends pillar sub-scores, composite Enterprise Risk Score (ERS), expected loss,
    and risk classification tiers.

    Parameters:
        df (pd.DataFrame): Ingested, validated enterprise dataset.
        config (RiskEngineConfig, optional): Weighting and threshold parameters.

    Returns:
        pd.DataFrame: Augmented DataFrame containing calculated metrics and ratings.
    """
    cfg = config or DEFAULT_CONFIG
    res = df.copy()

    # -------------------------------------------------------------------------
    # 1. Counterparty / Credit Risk Scoring (0 - 100 scale)
    # -------------------------------------------------------------------------
    # Map probability of default: 0% -> 0, 25%+ -> 100
    pd_score = np.clip(res["probability_of_default"] * 400.0, 0.0, 100.0)
    
    # Loss Given Default: scaled directly
    lgd_score = np.clip(res["loss_given_default"] * 100.0, 0.0, 100.0)

    # External rating baseline score
    rating_score = res["credit_rating"].map(cfg.rating_baseline_scores).fillna(50.0)

    # Debt-to-Equity leverage risk: D/E >= 5.0 indicates high leverage
    de_score = np.clip((res["debt_to_equity"] / 5.5) * 100.0, 0.0, 100.0)

    # Weighted Credit Risk Sub-Score
    credit_score = (
        0.40 * pd_score +
        0.25 * rating_score +
        0.20 * lgd_score +
        0.15 * de_score
    )
    res["credit_risk_score"] = np.round(np.clip(credit_score, 0.0, 100.0), 2)

    # Expected Loss (EL) = EAD * PD * LGD
    res["expected_loss_usd"] = np.round(
        res["total_exposure_usd"] * res["probability_of_default"] * res["loss_given_default"], 2
    )

    # -------------------------------------------------------------------------
    # 2. Financial & Liquidity Health Scoring (0 - 100 scale, 100 = max distress)
    # -------------------------------------------------------------------------
    # Current Ratio: CR >= 2.5 -> 0 risk; CR <= 0.5 -> 100 risk
    cr_score = np.clip(((2.5 - res["current_ratio"]) / 2.0) * 100.0, 0.0, 100.0)

    # Quick Ratio: QR >= 2.0 -> 0 risk; QR <= 0.3 -> 100 risk
    qr_score = np.clip(((2.0 - res["quick_ratio"]) / 1.7) * 100.0, 0.0, 100.0)

    # Interest Coverage Ratio: ICR >= 10.0 -> 0 risk; ICR <= 0.5 -> 100 risk
    icr_score = np.clip(((10.0 - res["interest_coverage_ratio"]) / 9.5) * 100.0, 0.0, 100.0)

    # Operating Margin: OM >= 0.30 -> 0 risk; OM <= -0.10 -> 100 risk
    om_score = np.clip(((0.30 - res["operating_margin"]) / 0.40) * 100.0, 0.0, 100.0)

    # Weighted Financial Distress Sub-Score
    financial_score = (
        0.35 * cr_score +
        0.25 * qr_score +
        0.25 * icr_score +
        0.15 * om_score
    )
    res["financial_risk_score"] = np.round(np.clip(financial_score, 0.0, 100.0), 2)

    # -------------------------------------------------------------------------
    # 3. Operational & Compliance Risk Scoring (0 - 100 scale)
    # -------------------------------------------------------------------------
    # Invert control effectiveness: 100% -> 0 risk, 0% -> 100 risk
    control_risk = 100.0 - res["control_effectiveness_score"]

    # Audit findings penalty: 0 -> 0 risk; 12+ findings -> 100 risk
    audit_score = np.clip(res["audit_findings_count"] * 8.33, 0.0, 100.0)

    # Incident frequency: 0 -> 0 risk; 14+ incidents -> 100 risk
    incident_score = np.clip(res["incident_frequency_annual"] * 7.14, 0.0, 100.0)

    # Regulatory compliance score inverted: 100% -> 0 risk, 0% -> 100 risk
    compliance_risk = 100.0 - res["regulatory_compliance_score"]

    # SLA breach penalty: 0% -> 0 risk; 33%+ breach -> 100 risk
    sla_score = np.clip(res["sla_breach_rate"] * 300.0, 0.0, 100.0)

    # Weighted Operational Risk Sub-Score
    ops_score = (
        0.30 * control_risk +
        0.25 * compliance_risk +
        0.20 * audit_score +
        0.15 * incident_score +
        0.10 * sla_score
    )
    res["operational_risk_score"] = np.round(np.clip(ops_score, 0.0, 100.0), 2)

    # -------------------------------------------------------------------------
    # 4. Composite Enterprise Risk Score (ERS)
    # -------------------------------------------------------------------------
    composite_ers = (
        cfg.weight_credit * res["credit_risk_score"] +
        cfg.weight_financial * res["financial_risk_score"] +
        cfg.weight_operational * res["operational_risk_score"]
    )
    res["composite_risk_score"] = np.round(np.clip(composite_ers, 0.0, 100.0), 2)

    # -------------------------------------------------------------------------
    # 5. Risk Classification Tiers (Low / Medium / High)
    # -------------------------------------------------------------------------
    conditions = [
        res["composite_risk_score"] < cfg.threshold_low,
        (res["composite_risk_score"] >= cfg.threshold_low) & (res["composite_risk_score"] < cfg.threshold_medium),
        res["composite_risk_score"] >= cfg.threshold_medium
    ]
    choices = ["Low Risk", "Medium Risk", "High Risk"]
    res["risk_tier"] = np.select(conditions, choices, default="Medium Risk")

    return res


def score_single_entity(
    record: Dict[str, Any],
    config: Optional[RiskEngineConfig] = None
) -> Dict[str, Any]:
    """
    Scores an individual enterprise counterparty dictionary and returns detailed metrics.
    """
    df_single = pd.DataFrame([record])
    df_scored = calculate_risk_scores(df_single, config=config)
    return df_scored.iloc[0].to_dict()
