"""
test_risk_engine.py
===================
Unit and integration tests for the quantitative scoring engine,
data loader schema validation, mitigation triggers, and edge cases.
"""

import pytest
import pandas as pd
import numpy as np

from data_loader.schema import EnterpriseRiskRecord
from data_loader.loader import load_risk_dataset
from risk_engine.config import RiskEngineConfig, DEFAULT_CONFIG
from risk_engine.scoring import calculate_risk_scores, score_single_entity
from risk_engine.mitigation import generate_mitigation_actions, generate_portfolio_decision_summary


@pytest.fixture
def sample_clean_df():
    """Provides a deterministic test DataFrame with known low, medium, and high risk profiles."""
    return pd.DataFrame([
        {
            "entity_id": "ENT-TEST-LOW",
            "entity_name": "Apex Prime Holdings Ltd",
            "sector": "Technology & Software",
            "jurisdiction": "North America",
            "credit_rating": "AAA",
            "annual_revenue_usd": 500_000_000.0,
            "total_exposure_usd": 10_000_000.0,
            "probability_of_default": 0.002,
            "loss_given_default": 0.20,
            "current_ratio": 3.0,
            "quick_ratio": 2.5,
            "debt_to_equity": 0.5,
            "interest_coverage_ratio": 20.0,
            "operating_margin": 0.25,
            "audit_findings_count": 0,
            "control_effectiveness_score": 95.0,
            "incident_frequency_annual": 0,
            "regulatory_compliance_score": 98.0,
            "sla_breach_rate": 0.01,
        },
        {
            "entity_id": "ENT-TEST-MED",
            "entity_name": "Midland Industrial Systems Corp",
            "sector": "Manufacturing & Industrial",
            "jurisdiction": "Western Europe",
            "credit_rating": "BBB",
            "annual_revenue_usd": 200_000_000.0,
            "total_exposure_usd": 8_000_000.0,
            "probability_of_default": 0.035,
            "loss_given_default": 0.45,
            "current_ratio": 1.5,
            "quick_ratio": 1.1,
            "debt_to_equity": 2.2,
            "interest_coverage_ratio": 4.5,
            "operating_margin": 0.12,
            "audit_findings_count": 4,
            "control_effectiveness_score": 72.0,
            "incident_frequency_annual": 3,
            "regulatory_compliance_score": 78.0,
            "sla_breach_rate": 0.05,
        },
        {
            "entity_id": "ENT-TEST-HIGH",
            "entity_name": "Distressed Logistics Group PLC",
            "sector": "Transportation & Logistics",
            "jurisdiction": "Asia-Pacific",
            "credit_rating": "CCC",
            "annual_revenue_usd": 80_000_000.0,
            "total_exposure_usd": 15_000_000.0,
            "probability_of_default": 0.22,
            "loss_given_default": 0.75,
            "current_ratio": 0.6,
            "quick_ratio": 0.4,
            "debt_to_equity": 6.2,
            "interest_coverage_ratio": -0.8,
            "operating_margin": -0.15,
            "audit_findings_count": 14,
            "control_effectiveness_score": 32.0,
            "incident_frequency_annual": 12,
            "regulatory_compliance_score": 38.0,
            "sla_breach_rate": 0.28,
        }
    ])


class TestRiskConfig:
    """Verifies configuration constraints and validation logic."""

    def test_default_config_weights_sum_to_one(self):
        cfg = DEFAULT_CONFIG
        total = round(cfg.weight_credit + cfg.weight_financial + cfg.weight_operational, 4)
        assert total == 1.0

    def test_invalid_weights_raise_value_error(self):
        with pytest.raises(ValueError):
            RiskEngineConfig(weight_credit=0.5, weight_financial=0.5, weight_operational=0.5)

    def test_threshold_ordering_validation(self):
        with pytest.raises(ValueError):
            RiskEngineConfig(threshold_low=70.0, threshold_medium=50.0)


class TestRiskScoringCalculations:
    """Verifies quantitative calculations, bounds, monotonicity, and risk tiers."""

    def test_scores_strictly_bounded(self, sample_clean_df):
        scored = calculate_risk_scores(sample_clean_df)
        
        for col in ["credit_risk_score", "financial_risk_score", "operational_risk_score", "composite_risk_score"]:
            assert (scored[col] >= 0.0).all(), f"{col} has values below 0"
            assert (scored[col] <= 100.0).all(), f"{col} has values above 100"

    def test_risk_tier_assignment(self, sample_clean_df):
        scored = calculate_risk_scores(sample_clean_df)
        
        low_row = scored[scored["entity_id"] == "ENT-TEST-LOW"].iloc[0]
        med_row = scored[scored["entity_id"] == "ENT-TEST-MED"].iloc[0]
        high_row = scored[scored["entity_id"] == "ENT-TEST-HIGH"].iloc[0]

        assert low_row["risk_tier"] == "Low Risk"
        assert med_row["risk_tier"] == "Medium Risk"
        assert high_row["risk_tier"] == "High Risk"

    def test_expected_loss_formula(self, sample_clean_df):
        scored = calculate_risk_scores(sample_clean_df)
        for _, row in scored.iterrows():
            expected = round(row["total_exposure_usd"] * row["probability_of_default"] * row["loss_given_default"], 2)
            assert pytest.approx(row["expected_loss_usd"], 0.01) == expected

    def test_score_sensitivity_and_monotonicity(self, sample_clean_df):
        scored = calculate_risk_scores(sample_clean_df)
        low_score = scored[scored["entity_id"] == "ENT-TEST-LOW"]["composite_risk_score"].iloc[0]
        med_score = scored[scored["entity_id"] == "ENT-TEST-MED"]["composite_risk_score"].iloc[0]
        high_score = scored[scored["entity_id"] == "ENT-TEST-HIGH"]["composite_risk_score"].iloc[0]

        assert low_score < med_score < high_score

    def test_single_entity_scorer_matches_batch(self, sample_clean_df):
        scored_batch = calculate_risk_scores(sample_clean_df)
        high_dict = sample_clean_df.iloc[2].to_dict()
        single_result = score_single_entity(high_dict)

        batch_result = scored_batch.iloc[2].to_dict()
        assert single_result["composite_risk_score"] == batch_result["composite_risk_score"]
        assert single_result["risk_tier"] == batch_result["risk_tier"]


class TestMitigationDecisionSupport:
    """Verifies rule-based decision support logic and tripwires."""

    def test_high_risk_triggers_critical_mitigations(self, sample_clean_df):
        scored = calculate_risk_scores(sample_clean_df)
        high_row = scored[scored["entity_id"] == "ENT-TEST-HIGH"].iloc[0]
        actions = generate_mitigation_actions(high_row)

        assert len(actions) >= 3
        categories = [a["category"] for a in actions]
        priorities = [a["priority"] for a in actions]

        assert "Counterparty Credit" in categories
        assert "Liquidity Health" in categories
        assert "Critical" in priorities

    def test_low_risk_entity_receives_advisory(self, sample_clean_df):
        scored = calculate_risk_scores(sample_clean_df)
        low_row = scored[scored["entity_id"] == "ENT-TEST-LOW"].iloc[0]
        actions = generate_mitigation_actions(low_row)

        assert len(actions) == 1
        assert actions[0]["category"] == "Routine Governance"
        assert actions[0]["priority"] == "Advisory"

    def test_portfolio_decision_summary_metrics(self, sample_clean_df):
        scored = calculate_risk_scores(sample_clean_df)
        summary = generate_portfolio_decision_summary(scored)

        assert summary["total_entities"] == 3
        assert summary["high_risk_count"] == 1
        assert summary["total_exposure_usd"] == 33_000_000.0


class TestEdgeCasesAndValidation:
    """Verifies resilience to extreme boundary values."""

    def test_zero_and_negative_ratios(self):
        extreme_df = pd.DataFrame([{
            "entity_id": "ENT-ZERO",
            "entity_name": "Zero Metrics LLC",
            "sector": "Financial Services",
            "jurisdiction": "North America",
            "credit_rating": "CCC",
            "annual_revenue_usd": 0.0,
            "total_exposure_usd": 0.0,
            "probability_of_default": 0.0,
            "loss_given_default": 0.0,
            "current_ratio": 0.0,
            "quick_ratio": 0.0,
            "debt_to_equity": 0.0,
            "interest_coverage_ratio": -10.0,
            "operating_margin": -0.80,
            "audit_findings_count": 0,
            "control_effectiveness_score": 0.0,
            "incident_frequency_annual": 0,
            "regulatory_compliance_score": 0.0,
            "sla_breach_rate": 0.0,
        }])
        scored = calculate_risk_scores(extreme_df)
        assert 0.0 <= scored["composite_risk_score"].iloc[0] <= 100.0
        assert scored["expected_loss_usd"].iloc[0] == 0.0

    def test_pydantic_schema_rejection(self):
        with pytest.raises(Exception):
            EnterpriseRiskRecord(
                entity_id="ENT-BAD",
                entity_name="Bad Entity",
                sector="Invalid Sector",  # Not in literal
                jurisdiction="North America",
                credit_rating="AAA",
                annual_revenue_usd=-500.0,  # Negative revenue
                total_exposure_usd=100.0,
                probability_of_default=1.5,  # > 1.0
                loss_given_default=0.5,
                current_ratio=1.0,
                quick_ratio=1.0,
                debt_to_equity=1.0,
                interest_coverage_ratio=2.0,
                operating_margin=0.1,
                audit_findings_count=0,
                control_effectiveness_score=80.0,
                incident_frequency_annual=0,
                regulatory_compliance_score=80.0,
                sla_breach_rate=0.0
            )
