"""
run_pipeline.py
===============
Reproducible CLI batch runner for the Enterprise Risk Assessment Pipeline.
Executes ingestion, schema validation, quantitative scoring, mitigation generation,
and exports executive reports.
"""

import os
import argparse
from dotenv import load_dotenv

from data_loader.loader import load_risk_dataset
from data_loader.synthetic_generator import generate_synthetic_risk_data
from risk_engine.config import RiskEngineConfig, DEFAULT_CONFIG
from risk_engine.scoring import calculate_risk_scores
from reporting.reports import generate_excel_risk_report, generate_executive_text_summary


def main():
    load_dotenv()
    parser = argparse.ArgumentParser(
        description="Enterprise Risk Assessment & Decision Support System - Analytics Pipeline Runner"
    )
    parser.add_argument(
        "--source",
        type=str,
        default="data/enterprise_risk_dataset.csv",
        help="Path to CSV or SQLite risk dataset (default: data/enterprise_risk_dataset.csv)"
    )
    parser.add_argument(
        "--regenerate-data",
        action="store_true",
        help="Generate a fresh synthetic dataset before running the pipeline."
    )
    parser.add_argument(
        "--records",
        type=int,
        default=750,
        help="Number of synthetic records to generate if --regenerate-data is passed."
    )
    parser.add_argument(
        "--weight-credit",
        type=float,
        default=0.40,
        help="Weight for Credit & Counterparty pillar (default: 0.40)"
    )
    parser.add_argument(
        "--weight-financial",
        type=float,
        default=0.35,
        help="Weight for Financial & Liquidity pillar (default: 0.35)"
    )
    parser.add_argument(
        "--weight-operational",
        type=float,
        default=0.25,
        help="Weight for Operational & Compliance pillar (default: 0.25)"
    )
    parser.add_argument(
        "--export-excel",
        type=str,
        default="data/enterprise_risk_assessment_report.xlsx",
        help="Target output path for the executive Excel report."
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress terminal summary output."
    )

    args = parser.parse_args()

    # 1. Regenerate data if requested or if file missing
    if args.regenerate_data or not os.path.exists(args.source):
        print(f"[*] Generating {args.records} synthetic enterprise risk records...")
        os.makedirs(os.path.dirname(args.source) or ".", exist_ok=True)
        generate_synthetic_risk_data(
            num_records=args.records,
            seed=42,
            csv_path=args.source,
            sqlite_path="data/enterprise_risk.db"
        )
        print(f"[+] Dataset saved to: {args.source}")

    # 2. Ingestion & Validation
    print(f"[*] Ingesting dataset from: {args.source}")
    df_raw, val_report = load_risk_dataset(args.source, validate=True)
    print(f"[+] Ingestion complete. Records: {val_report.total_records} | Valid: {val_report.valid_records} | Invalid: {val_report.invalid_records}")

    if not val_report.validation_passed:
        print("[!] Validation warnings detected:")
        for err in val_report.errors_detected:
            print(f"    - {err}")

    # 3. Quantitative Risk Scoring
    print("[*] Computing quantitative multi-pillar risk models...")
    config = RiskEngineConfig(
        weight_credit=args.weight_credit,
        weight_financial=args.weight_financial,
        weight_operational=args.weight_operational
    )
    df_scored = calculate_risk_scores(df_raw, config=config)
    print("[+] Risk scoring complete. Computed Credit, Liquidity, Ops, and Composite ERS.")

    # 4. Reporting & Export
    if not args.quiet:
        summary_text = generate_executive_text_summary(df_scored)
        print(summary_text)

    if args.export_excel:
        os.makedirs(os.path.dirname(args.export_excel) or ".", exist_ok=True)
        excel_bytes = generate_excel_risk_report(df_scored)
        with open(args.export_excel, "wb") as f:
            f.write(excel_bytes)
        print(f"[+] Executive 4-Sheet Excel workbook successfully exported to: {args.export_excel}")


if __name__ == "__main__":
    main()
