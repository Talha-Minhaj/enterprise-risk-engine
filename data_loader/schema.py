"""
schema.py
=========
Pydantic data schemas, validation constraints, and quality checks
for enterprise financial, counterparty, and operational risk metrics.
"""

from typing import List, Optional, Literal
from pydantic import BaseModel, Field, field_validator


# Standard credit rating categories
CreditRatingTier = Literal["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]

# Enterprise business sectors
IndustrySector = Literal[
    "Financial Services",
    "Energy & Utilities",
    "Technology & Software",
    "Healthcare & Life Sciences",
    "Manufacturing & Industrial",
    "Retail & Consumer Goods",
    "Transportation & Logistics",
    "Telecommunications"
]

# Geographic jurisdictions
JurisdictionRegion = Literal[
    "North America",
    "Western Europe",
    "Asia-Pacific",
    "Latin America",
    "Middle East & Africa"
]


class EnterpriseRiskRecord(BaseModel):
    """
    Normalized data schema for an enterprise risk counterparty or business unit.
    Captures counterparty credit exposure, liquidity metrics, and operational compliance.
    """
    entity_id: str = Field(description="Unique sanitized entity code, e.g., ENT-1042")
    entity_name: str = Field(description="Sanitized synthetic corporate entity name")
    sector: IndustrySector = Field(description="Primary industry classification")
    jurisdiction: JurisdictionRegion = Field(description="Primary operating jurisdiction")
    credit_rating: CreditRatingTier = Field(description="Standardized credit rating tier")
    annual_revenue_usd: float = Field(ge=0, description="Annual corporate revenue in USD")
    total_exposure_usd: float = Field(ge=0, description="Total Exposure at Default (EAD) in USD")
    
    # Quantitative Credit & Counterparty Factors
    probability_of_default: float = Field(
        ge=0.0, le=1.0, 
        description="1-Year Probability of Default (PD) between 0.0 and 1.0"
    )
    loss_given_default: float = Field(
        ge=0.0, le=1.0, 
        description="Loss Given Default (LGD) expectation between 0.0 and 1.0"
    )
    
    # Financial Solvency & Liquidity Ratios
    current_ratio: float = Field(
        ge=0.0, 
        description="Current Assets / Current Liabilities (Liquidity buffer)"
    )
    quick_ratio: float = Field(
        ge=0.0, 
        description="(Cash + Marketable Securities + Receivables) / Current Liabilities"
    )
    debt_to_equity: float = Field(
        ge=0.0, 
        description="Total Debt / Total Shareholder Equity (Leverage ratio)"
    )
    interest_coverage_ratio: float = Field(
        description="EBIT / Interest Expense (Ability to service debt)"
    )
    operating_margin: float = Field(
        ge=-1.0, le=1.0, 
        description="Operating Income / Revenue (Operational profitability)"
    )
    
    # Operational Risk & Regulatory Compliance Metrics
    audit_findings_count: int = Field(
        ge=0, 
        description="Number of unresolved internal/external audit findings in last 12 months"
    )
    control_effectiveness_score: float = Field(
        ge=0.0, le=100.0, 
        description="Internal controls maturity & effectiveness index (0-100)"
    )
    incident_frequency_annual: int = Field(
        ge=0, 
        description="Number of critical operational or security incidents in past year"
    )
    regulatory_compliance_score: float = Field(
        ge=0.0, le=100.0, 
        description="Regulatory & statutory compliance rating (0-100)"
    )
    sla_breach_rate: float = Field(
        ge=0.0, le=1.0, 
        description="Contractual service level agreement breach rate (0.0 to 1.0)"
    )

    @field_validator("entity_id")
    @classmethod
    def validate_entity_id(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("entity_id cannot be blank")
        return v.strip().upper()


class RiskDatasetValidationReport(BaseModel):
    """Summary diagnostic report of dataset validation checks."""
    total_records: int
    valid_records: int
    invalid_records: int
    validation_passed: bool
    errors_detected: List[str] = Field(default_factory=list)
