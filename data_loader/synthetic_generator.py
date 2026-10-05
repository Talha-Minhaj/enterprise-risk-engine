"""
synthetic_generator.py
======================
Generates a realistic, statistically coherent synthetic mock dataset
representing 500-1000 enterprise counterparty risk profiles.
Completely scrubbed of any proprietary or confidential client information.
"""

import os
import random
import sqlite3
import pandas as pd
import numpy as np
from typing import Optional


# Corporate naming components for synthetic generator
PREFIXES = [
    "Apex", "Vanguard", "Meridian", "Pinnacle", "Horizon", "Atlas", "Beacon", "Crestview",
    "Delta", "Echo", "Falcon", "Genesis", "Hyperion", "Infinity", "Jupiter", "Kestrel",
    "Luminary", "Matrix", "Nexus", "Olympus", "Pacific", "Quantum", "Radiant", "Summit",
    "Titan", "Unity", "Vertex", "Zephyr", "Aegis", "Solstice", "Terra", "Nova"
]

CORES = [
    "Global Logistics", "Renewable Power", "Health Solutions", "Semiconductor", "Capital Partners",
    "Chemical Dynamics", "Aerospace Engineering", "Digital Systems", "Energy Infrastructure",
    "Biomedical Research", "Supply Chain Network", "Industrial Robotics", "Telecom Networks",
    "Maritime Transport", "Consumer Brands", "Cloud Technologies", "Advanced Materials",
    "Financial Services", "Automotive Systems", "Agri-Sciences", "Secure Payments"
]

SUFFIXES = ["Corp", "Inc", "LLC", "Holdings", "Group", "PLC", "Ltd", "International", "Enterprises"]

SECTORS = [
    "Financial Services",
    "Energy & Utilities",
    "Technology & Software",
    "Healthcare & Life Sciences",
    "Manufacturing & Industrial",
    "Retail & Consumer Goods",
    "Transportation & Logistics",
    "Telecommunications"
]

JURISDICTIONS = [
    "North America",
    "Western Europe",
    "Asia-Pacific",
    "Latin America",
    "Middle East & Africa"
]

# Rating distribution: weighted towards investment grade, realistic tail for distressed
RATINGS = ["AAA", "AA", "A", "BBB", "BB", "B", "CCC"]
RATING_WEIGHTS = [0.08, 0.16, 0.28, 0.26, 0.12, 0.07, 0.03]

# Base characteristics mapped by credit rating tier to ensure macroeconomic realism
RATING_PROFILES = {
    "AAA": {"pd_range": (0.001, 0.004), "lgd_range": (0.15, 0.35), "cr_range": (2.0, 4.0), "de_range": (0.2, 0.9), "icr_range": (12.0, 25.0), "ctrl_range": (88.0, 99.0), "audit_max": 2, "inc_max": 2},
    "AA":  {"pd_range": (0.003, 0.009), "lgd_range": (0.20, 0.40), "cr_range": (1.8, 3.2), "de_range": (0.4, 1.4), "icr_range": (8.0, 18.0),  "ctrl_range": (82.0, 95.0), "audit_max": 3, "inc_max": 3},
    "A":   {"pd_range": (0.008, 0.020), "lgd_range": (0.25, 0.45), "cr_range": (1.5, 2.6), "de_range": (0.8, 2.0), "icr_range": (5.0, 12.0),  "ctrl_range": (75.0, 90.0), "audit_max": 5, "inc_max": 4},
    "BBB": {"pd_range": (0.018, 0.045), "lgd_range": (0.30, 0.52), "cr_range": (1.2, 2.1), "de_range": (1.3, 2.8), "icr_range": (3.0, 7.5),   "ctrl_range": (65.0, 82.0), "audit_max": 7, "inc_max": 6},
    "BB":  {"pd_range": (0.040, 0.090), "lgd_range": (0.38, 0.62), "cr_range": (0.9, 1.6), "de_range": (2.2, 4.2), "icr_range": (1.5, 4.0),   "ctrl_range": (52.0, 72.0), "audit_max": 9, "inc_max": 8},
    "B":   {"pd_range": (0.080, 0.160), "lgd_range": (0.45, 0.72), "cr_range": (0.6, 1.2), "de_range": (3.2, 5.8), "icr_range": (0.5, 2.2),   "ctrl_range": (40.0, 62.0), "audit_max": 12, "inc_max": 12},
    "CCC": {"pd_range": (0.150, 0.280), "lgd_range": (0.55, 0.85), "cr_range": (0.4, 0.9), "de_range": (4.5, 7.5), "icr_range": (-1.5, 1.1),  "ctrl_range": (25.0, 50.0), "audit_max": 16, "inc_max": 16},
}


def generate_synthetic_risk_data(
    num_records: int = 750,
    seed: int = 42,
    csv_path: Optional[str] = None,
    sqlite_path: Optional[str] = None
) -> pd.DataFrame:
    """
    Synthesizes a realistic, multi-factor risk dataset for enterprise portfolio analysis.

    Parameters:
        num_records (int): Number of synthetic enterprise rows (default: 750).
        seed (int): Reproducibility random seed.
        csv_path (str, optional): Target CSV filepath to persist dataset.
        sqlite_path (str, optional): Target SQLite database filepath.

    Returns:
        pd.DataFrame: Clean DataFrame ready for ingestion and analytics.
    """
    random.seed(seed)
    np.random.seed(seed)

    records = []
    used_names = set()

    for i in range(1, num_records + 1):
        entity_id = f"ENT-{1000 + i}"

        # Generate unique realistic corporate name
        while True:
            name = f"{random.choice(PREFIXES)} {random.choice(CORES)} {random.choice(SUFFIXES)}"
            if name not in used_names:
                used_names.add(name)
                break

        sector = random.choice(SECTORS)
        jurisdiction = random.choice(JURISDICTIONS)
        
        # Credit rating sample based on distribution
        rating = np.random.choice(RATINGS, p=RATING_WEIGHTS)
        profile = RATING_PROFILES[rating]

        # Financial dimensions
        # Revenue: Lognormally distributed between $15M and $12B
        log_rev = np.random.uniform(np.log(15_000_000), np.log(12_000_000_000))
        revenue = round(float(np.exp(log_rev)), 2)

        # Exposure at Default (EAD): correlated with revenue size
        exposure_pct = np.random.uniform(0.01, 0.08)
        exposure = round(float(revenue * exposure_pct), 2)
        # Cap exposure between $500k and $250M
        exposure = max(500_000.0, min(250_000_000.0, exposure))

        # Credit & Counterparty metrics
        pd_val = round(float(np.random.uniform(*profile["pd_range"])), 4)
        lgd_val = round(float(np.random.uniform(*profile["lgd_range"])), 4)

        # Liquidity & Solvency Ratios
        current_ratio = round(float(np.random.uniform(*profile["cr_range"])), 2)
        quick_ratio = round(float(max(0.2, current_ratio * np.random.uniform(0.65, 0.90))), 2)
        debt_to_equity = round(float(np.random.uniform(*profile["de_range"])), 2)
        interest_coverage = round(float(np.random.uniform(*profile["icr_range"])), 2)
        operating_margin = round(float(np.random.uniform(-0.10, 0.35) if rating in ["B", "CCC"] else np.random.uniform(0.08, 0.38)), 4)

        # Operational & Governance metrics
        control_score = round(float(np.random.uniform(*profile["ctrl_range"])), 1)
        audit_findings = int(np.random.randint(0, profile["audit_max"] + 1))
        incident_freq = int(np.random.randint(0, profile["inc_max"] + 1))
        
        # Compliance score: correlates with controls
        compliance_noise = np.random.uniform(-8.0, 5.0)
        compliance_score = round(float(max(15.0, min(100.0, control_score + compliance_noise))), 1)
        
        # SLA breach rate: inversely correlated with control score
        base_sla_breach = (100.0 - control_score) / 250.0
        sla_breach_rate = round(float(max(0.005, min(0.35, base_sla_breach + np.random.uniform(-0.02, 0.05)))), 4)

        records.append({
            "entity_id": entity_id,
            "entity_name": name,
            "sector": sector,
            "jurisdiction": jurisdiction,
            "credit_rating": rating,
            "annual_revenue_usd": revenue,
            "total_exposure_usd": exposure,
            "probability_of_default": pd_val,
            "loss_given_default": lgd_val,
            "current_ratio": current_ratio,
            "quick_ratio": quick_ratio,
            "debt_to_equity": debt_to_equity,
            "interest_coverage_ratio": interest_coverage,
            "operating_margin": operating_margin,
            "audit_findings_count": audit_findings,
            "control_effectiveness_score": control_score,
            "incident_frequency_annual": incident_freq,
            "regulatory_compliance_score": compliance_score,
            "sla_breach_rate": sla_breach_rate
        })

    df = pd.DataFrame(records)

    # Export to CSV if target path provided
    if csv_path:
        os.makedirs(os.path.dirname(csv_path), exist_ok=True)
        df.to_csv(csv_path, index=False)

    # Export to SQLite if target path provided
    if sqlite_path:
        os.makedirs(os.path.dirname(sqlite_path), exist_ok=True)
        conn = sqlite3.connect(sqlite_path)
        df.to_sql("enterprise_risk_records", conn, if_exists="replace", index=False)
        conn.close()

    return df


if __name__ == "__main__":
    out_csv = os.path.join("data", "enterprise_risk_dataset.csv")
    out_db = os.path.join("data", "enterprise_risk.db")
    df_gen = generate_synthetic_risk_data(num_records=750, seed=42, csv_path=out_csv, sqlite_path=out_db)
    print(f"Generated {len(df_gen)} synthetic enterprise risk records.")
    print(f"Saved to {out_csv} and {out_db}.")
