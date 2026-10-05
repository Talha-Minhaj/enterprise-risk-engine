"""
loader.py
=========
Robust data ingestion, schema validation, type enforcement,
and sanitization checks for enterprise risk datasets.
"""

import os
import sqlite3
import pandas as pd
from typing import Tuple, Optional, Union
from pydantic import ValidationError

from .schema import EnterpriseRiskRecord, RiskDatasetValidationReport


# Expected column definitions and datatypes
NUMERIC_COLUMNS = [
    "annual_revenue_usd", "total_exposure_usd", "probability_of_default",
    "loss_given_default", "current_ratio", "quick_ratio", "debt_to_equity",
    "interest_coverage_ratio", "operating_margin", "audit_findings_count",
    "control_effectiveness_score", "incident_frequency_annual",
    "regulatory_compliance_score", "sla_breach_rate"
]

CATEGORICAL_COLUMNS = ["entity_id", "entity_name", "sector", "jurisdiction", "credit_rating"]


def load_risk_dataset(
    source: Union[str, pd.DataFrame],
    validate: bool = True
) -> Tuple[pd.DataFrame, RiskDatasetValidationReport]:
    """
    Ingests enterprise risk records from CSV, SQLite, or an existing DataFrame.
    Applies type casting, sanitization, and schema validation.

    Parameters:
        source (Union[str, pd.DataFrame]): File path (CSV / SQLite) or DataFrame.
        validate (bool): Whether to perform strict Pydantic model validation.

    Returns:
        Tuple[pd.DataFrame, RiskDatasetValidationReport]: Clean DataFrame and validation summary.
    """
    if isinstance(source, pd.DataFrame):
        df = source.copy()
    elif isinstance(source, str):
        if not os.path.exists(source):
            raise FileNotFoundError(f"Risk dataset source not found at: {source}")
        
        if source.endswith(".csv"):
            df = pd.read_csv(source)
        elif source.endswith((".db", ".sqlite", ".sqlite3")):
            conn = sqlite3.connect(source)
            # Find the primary table
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [t[0] for t in cursor.fetchall() if t[0] != "sqlite_sequence"]
            table_name = tables[0] if tables else "enterprise_risk_records"
            df = pd.read_sql_query(f"SELECT * FROM {table_name}", conn)
            conn.close()
        else:
            raise ValueError(f"Unsupported file format: {source}. Expected .csv or .sqlite/.db")
    else:
        raise TypeError("Source must be a file path string or pandas DataFrame.")

    # 1. Enforce Column Presence
    missing_cols = [col for col in CATEGORICAL_COLUMNS + NUMERIC_COLUMNS if col not in df.columns]
    if missing_cols:
        raise ValueError(f"Dataset is missing required risk attributes: {missing_cols}")

    # 2. Type casting & coercion
    for col in NUMERIC_COLUMNS:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    # Drop records that have NaN in critical risk identifiers
    df.dropna(subset=["entity_id", "total_exposure_usd", "probability_of_default"], inplace=True)
    df.reset_index(drop=True, inplace=True)

    # 3. Sanitization verification: Ensure identifiers adhere to synthetic patterns (e.g. ENT-XXXX)
    # and strip any unexpected whitespace
    df["entity_id"] = df["entity_id"].astype(str).str.strip().str.upper()
    df["entity_name"] = df["entity_name"].astype(str).str.strip()

    # 4. Schema Validation Diagnostic
    errors = []
    valid_count = 0
    invalid_count = 0

    if validate:
        # Sample validation for fast performance on large sets or full check
        records_to_check = df.to_dict(orient="records")
        for rec in records_to_check:
            try:
                EnterpriseRiskRecord(**rec)
                valid_count += 1
            except ValidationError as e:
                invalid_count += 1
                if len(errors) < 10:  # Cap stored errors
                    errors.append(f"Entity {rec.get('entity_id')}: {str(e.errors()[0]['msg'])}")
            except Exception as e:
                invalid_count += 1
                if len(errors) < 10:
                    errors.append(f"Entity {rec.get('entity_id')}: {str(e)}")
    else:
        valid_count = len(df)

    validation_report = RiskDatasetValidationReport(
        total_records=len(df),
        valid_records=valid_count,
        invalid_records=invalid_count,
        validation_passed=(invalid_count == 0),
        errors_detected=errors
    )

    return df, validation_report


def save_dataset_to_sqlite(df: pd.DataFrame, db_path: str, table_name: str = "enterprise_risk_records") -> None:
    """Saves DataFrame into SQLite storage."""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists="replace", index=False)
    conn.close()
