"""
config.py
=========
Hyperparameters, weightings, classification thresholds,
and rating ordinal mappings for the Enterprise Risk Engine.
"""

from typing import Dict
from pydantic import BaseModel, Field, model_validator


class RiskEngineConfig(BaseModel):
    """Configuration container for risk engine weightings and thresholds."""
    
    # Pillar Weightings (Sum must equal 1.0)
    weight_credit: float = Field(default=0.40, ge=0.0, le=1.0, description="Weight for Counterparty Credit Risk")
    weight_financial: float = Field(default=0.35, ge=0.0, le=1.0, description="Weight for Financial & Liquidity Health")
    weight_operational: float = Field(default=0.25, ge=0.0, le=1.0, description="Weight for Operational & Compliance Risk")

    # Risk Tier Classification Cutoffs (0 - 100 scale)
    threshold_low: float = Field(default=35.0, ge=0.0, le=100.0, description="Upper bound for Low Risk tier")
    threshold_medium: float = Field(default=65.0, ge=0.0, le=100.0, description="Upper bound for Medium Risk tier")
    
    # Financial Stress Benchmark Thresholds
    crit_current_ratio: float = Field(default=1.0, description="Current ratio below which liquidity risk is critical")
    crit_interest_coverage: float = Field(default=1.5, description="ICR below which debt service is critical")
    crit_debt_to_equity: float = Field(default=3.5, description="D/E above which leverage is high")
    crit_probability_of_default: float = Field(default=0.05, description="PD above which counterparty risk is critical")
    crit_control_effectiveness: float = Field(default=60.0, description="Control score below which operational risk is critical")
    crit_audit_findings: int = Field(default=5, description="Audit findings above which governance is high risk")

    # Standardized credit rating ordinal mapping to numeric risk baseline (0-100)
    rating_baseline_scores: Dict[str, float] = Field(
        default={
            "AAA": 5.0,
            "AA": 15.0,
            "A": 30.0,
            "BBB": 48.0,
            "BB": 65.0,
            "B": 82.0,
            "CCC": 95.0,
        }
    )

    @model_validator(mode="after")
    def validate_weights_and_thresholds(self):
        total_weight = round(self.weight_credit + self.weight_financial + self.weight_operational, 4)
        if total_weight != 1.0:
            raise ValueError(
                f"Risk weights must sum to 1.0. Current sum: {total_weight} "
                f"({self.weight_credit} + {self.weight_financial} + {self.weight_operational})"
            )
        if self.threshold_low >= self.threshold_medium:
            raise ValueError("threshold_low must be strictly less than threshold_medium.")
        return self


# Default singleton instance
DEFAULT_CONFIG = RiskEngineConfig()
