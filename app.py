"""
app.py
======
Enterprise Risk Assessment & Decision Support System
A unified quantitative risk analytics platform and decision support dashboard
for enterprise counterparty, financial distress, operational compliance, and strategic transformation risks.
"""

import os
import io
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Load environment configuration
load_dotenv()

from data_loader.loader import load_risk_dataset, save_dataset_to_sqlite
from data_loader.synthetic_generator import generate_synthetic_risk_data
from risk_engine.config import RiskEngineConfig
from risk_engine.scoring import calculate_risk_scores, score_single_entity
from risk_engine.mitigation import (
    generate_mitigation_actions,
    generate_portfolio_decision_summary,
    generate_ai_risk_brief,
)
from risk_engine.consulting_suite import generate_consulting_suite
from reporting.reports import generate_excel_risk_report
from reporting.visualizer import (
    plot_risk_tier_distribution,
    plot_exposure_vs_risk,
    plot_sector_risk_breakdown,
    plot_entity_spider_radar,
)

# ---------------------------------------------------------------------------
# Streamlit Page Configuration
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="Enterprise Risk Assessment & Decision Support System",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ---------------------------------------------------------------------------
# Custom CSS for Modern Executive Aesthetics
# ---------------------------------------------------------------------------
st.markdown("""
<style>
    /* Dark executive theme baseline */
    .stApp {
        background-color: #0B0F17;
        color: #F1F5F9;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
    }
    
    /* Header hero container */
    .header-hero {
        background: linear-gradient(135deg, #1E293B 0%, #0F172A 100%);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 16px;
        padding: 2.0rem 2.4rem;
        margin-bottom: 1.8rem;
        box-shadow: 0 12px 36px -12px rgba(0, 0, 0, 0.6);
    }
    .header-hero-title {
        font-size: 2.3rem;
        font-weight: 800;
        background: linear-gradient(90deg, #60A5FA 0%, #38BDF8 50%, #93C5FD 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0 0 0.4rem 0;
        letter-spacing: -0.025em;
    }
    .header-hero-subtitle {
        color: #94A3B8;
        font-size: 1.05rem;
        font-weight: 400;
        margin: 0;
    }

    /* KPI metric cards */
    .kpi-container {
        background: rgba(30, 41, 59, 0.65);
        backdrop-filter: blur(8px);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 1.2rem 1.4rem;
        text-align: center;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
    }
    .kpi-title {
        font-size: 0.80rem;
        color: #94A3B8;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        margin-bottom: 0.35rem;
    }
    .kpi-value {
        font-size: 1.85rem;
        font-weight: 700;
        color: #F8FAFC;
    }
    .kpi-sub {
        font-size: 0.82rem;
        color: #64748B;
        margin-top: 0.2rem;
    }

    /* Sidebar adjustments */
    section[data-testid="stSidebar"] {
        background-color: #0F172A;
        border-right: 1px solid rgba(255, 255, 255, 0.07);
    }

    /* Badges */
    .badge-critical {
        background-color: rgba(239, 68, 68, 0.22);
        color: #FCA5A5;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.82rem;
        border: 1px solid rgba(239, 68, 68, 0.4);
    }
    .badge-high {
        background-color: rgba(249, 115, 22, 0.22);
        color: #FDBA74;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.82rem;
        border: 1px solid rgba(249, 115, 22, 0.4);
    }
    .badge-medium {
        background-color: rgba(245, 158, 11, 0.22);
        color: #FCD34D;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.82rem;
        border: 1px solid rgba(245, 158, 11, 0.4);
    }
    .badge-low {
        background-color: rgba(16, 185, 129, 0.22);
        color: #6EE7B7;
        padding: 0.25rem 0.65rem;
        border-radius: 6px;
        font-weight: 600;
        font-size: 0.82rem;
        border: 1px solid rgba(16, 185, 129, 0.4);
    }

    /* Mitigation action cards */
    .mitigation-card {
        background: #1E293B;
        border-left: 4px solid #38BDF8;
        border-radius: 8px;
        padding: 1.1rem 1.3rem;
        margin-bottom: 0.9rem;
        border-top: 1px solid rgba(255, 255, 255, 0.05);
        border-right: 1px solid rgba(255, 255, 255, 0.05);
        border-bottom: 1px solid rgba(255, 255, 255, 0.05);
    }
    .mitigation-card.critical {
        border-left-color: #EF4444;
    }
    .mitigation-card.high {
        border-left-color: #F97316;
    }
</style>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data Caching & Scoring Pipeline Initialization
# ---------------------------------------------------------------------------
@st.cache_data
def get_or_create_portfolio(
    csv_path: str = "data/enterprise_risk_dataset.csv",
    w_credit: float = 0.40,
    w_fin: float = 0.35,
    w_ops: float = 0.25,
    th_low: float = 35.0,
    th_med: float = 65.0
) -> pd.DataFrame:
    """Ingests dataset and computes multi-pillar risk model scores."""
    if not os.path.exists(csv_path):
        os.makedirs(os.path.dirname(csv_path) or ".", exist_ok=True)
        generate_synthetic_risk_data(
            num_records=750,
            seed=42,
            csv_path=csv_path,
            sqlite_path="data/enterprise_risk.db"
        )

    df_raw, _ = load_risk_dataset(csv_path, validate=False)
    cfg = RiskEngineConfig(
        weight_credit=w_credit,
        weight_financial=w_fin,
        weight_operational=w_ops,
        threshold_low=th_low,
        threshold_medium=th_med
    )
    return calculate_risk_scores(df_raw, config=cfg)


# ---------------------------------------------------------------------------
# Sidebar Configuration & Controls
# ---------------------------------------------------------------------------
with st.sidebar:
    st.image("https://img.icons8.com/fluency/96/shield.png", width=56)
    st.title("Risk System Controls")
    st.caption("Quantitative Risk Configuration")

    st.markdown("---")
    st.subheader("⚖️ Scoring Pillar Weights")
    w_credit = st.slider("Counterparty Credit Weight", min_value=0.10, max_value=0.70, value=0.40, step=0.05)
    w_financial = st.slider("Financial & Liquidity Weight", min_value=0.10, max_value=0.70, value=0.35, step=0.05)
    # Automatically compute operational weight to ensure exact sum = 1.0
    w_operational = round(1.0 - (w_credit + w_financial), 2)
    st.info(f"Operational & Compliance Weight: **{w_operational:.2f}** (Auto-balanced to 1.0)")

    if w_operational < 0.05 or w_operational > 0.80:
        st.error("Weights configuration out of valid operational bounds.")

    st.markdown("---")
    st.subheader("🎯 Classification Cutoffs")
    th_low = st.slider("Low Risk Threshold (Max)", min_value=20.0, max_value=45.0, value=35.0, step=1.0)
    th_med = st.slider("High Risk Threshold (Min)", min_value=50.0, max_value=80.0, value=65.0, step=1.0)

    st.markdown("---")
    st.subheader("🔑 AI Advisory Settings")
    default_key = os.environ.get("GEMINI_API_KEY", "")
    api_key_input = st.text_input(
        "Google Gemini API Key",
        value=default_key,
        type="password",
        help="Optional: Enables AI Executive Risk Briefings and Strategic Transformation Advisory."
    )
    gemini_model = st.selectbox(
        "Gemini Model Architecture",
        options=["gemini-2.5-flash", "gemini-1.5-pro", "gemini-1.5-flash"],
        index=0
    )

    st.markdown("---")
    st.caption("Enterprise Risk Assessment & Decision Support System v2.0")


# ---------------------------------------------------------------------------
# Load and Score Portfolio
# ---------------------------------------------------------------------------
df_scored = get_or_create_portfolio(
    w_credit=w_credit,
    w_fin=w_financial,
    w_ops=w_operational,
    th_low=th_low,
    th_med=th_med
)
summary = generate_portfolio_decision_summary(df_scored)

# ---------------------------------------------------------------------------
# Hero Header
# ---------------------------------------------------------------------------
st.markdown("""
<div class="header-hero">
    <div class="header-hero-title">Enterprise Risk Assessment & Decision Support System</div>
    <div class="header-hero-subtitle">Multi-Pillar Quantitative Risk Scoring, Prescriptive Decision Logic & Strategic Transformation Advisory</div>
</div>
""", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Main Navigation Tabs
# ---------------------------------------------------------------------------
tab_portfolio, tab_entity, tab_strategic, tab_data_export = st.tabs([
    "📊 Portfolio Risk Radar",
    "🔍 Counterparty Deep-Dive & Action Plan",
    "🚀 Strategic Transformation Advisor",
    "📥 Reporting & Data Center"
])


# ===========================================================================
# TAB 1: PORTFOLIO RISK RADAR
# ===========================================================================
with tab_portfolio:
    # KPI Row
    k1, k2, k3, k4, k5 = st.columns(5)
    with k1:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-title">Total Portfolio EAD</div>
            <div class="kpi-value">${(summary['total_exposure_usd'] / 1e9):.2f}B</div>
            <div class="kpi-sub">{summary['total_entities']:,} Active Counterparties</div>
        </div>
        """, unsafe_allow_html=True)
    with k2:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-title">Total Expected Loss</div>
            <div class="kpi-value" style="color: #38BDF8;">${(summary['total_expected_loss_usd'] / 1e6):.1f}M</div>
            <div class="kpi-sub">Loss Rate: {summary['portfolio_loss_rate_pct']:.2f}%</div>
        </div>
        """, unsafe_allow_html=True)
    with k3:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-title">Mean Risk Score (ERS)</div>
            <div class="kpi-value">{summary['average_composite_score']:.1f}</div>
            <div class="kpi-sub">Scale: 0 (Prime) to 100</div>
        </div>
        """, unsafe_allow_html=True)
    with k4:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-title">High-Risk Entities</div>
            <div class="kpi-value" style="color: #EF4444;">{summary['high_risk_count']:,}</div>
            <div class="kpi-sub">{summary['high_risk_percentage']:.1f}% of Total Portfolio</div>
        </div>
        """, unsafe_allow_html=True)
    with k5:
        st.markdown(f"""
        <div class="kpi-container">
            <div class="kpi-title">High-Risk Exposure</div>
            <div class="kpi-value" style="color: #F87171;">${(summary['high_risk_exposure_usd'] / 1e9):.2f}B</div>
            <div class="kpi-sub">Priority Capital at Risk</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Interactive Visualizations
    col_chart1, col_chart2 = st.columns([3, 2])
    with col_chart1:
        st.plotly_chart(plot_exposure_vs_risk(df_scored), use_container_width=True)
    with col_chart2:
        st.plotly_chart(plot_risk_tier_distribution(df_scored), use_container_width=True)

    st.plotly_chart(plot_sector_risk_breakdown(df_scored), use_container_width=True)

    # Watchlist Section with Dynamic Filtering
    st.markdown("### ⚠️ Priority Counterparty Risk Watchlist")
    st.caption("Entities requiring immediate executive scrutiny, collateral reinforcement, or risk mitigation covenants.")

    # Filter Bar
    f1, f2, f3, f4 = st.columns(4)
    with f1:
        selected_tier = st.multiselect("Risk Tier", options=["High Risk", "Medium Risk", "Low Risk"], default=["High Risk"])
    with f2:
        sectors = sorted(df_scored["sector"].unique())
        selected_sector = st.multiselect("Industry Sector", options=sectors, default=[])
    with f3:
        regions = sorted(df_scored["jurisdiction"].unique())
        selected_region = st.multiselect("Jurisdiction", options=regions, default=[])
    with f4:
        search_query = st.text_input("Search Entity Name or ID", "")

    # Apply filters
    filtered_df = df_scored.copy()
    if selected_tier:
        filtered_df = filtered_df[filtered_df["risk_tier"].isin(selected_tier)]
    if selected_sector:
        filtered_df = filtered_df[filtered_df["sector"].isin(selected_sector)]
    if selected_region:
        filtered_df = filtered_df[filtered_df["jurisdiction"].isin(selected_region)]
    if search_query.strip():
        q = search_query.strip().lower()
        filtered_df = filtered_df[
            filtered_df["entity_name"].str.lower().str.contains(q) |
            filtered_df["entity_id"].str.lower().str.contains(q)
        ]

    # Format Watchlist Table
    display_df = filtered_df[[
        "entity_id", "entity_name", "sector", "credit_rating", "total_exposure_usd",
        "expected_loss_usd", "composite_risk_score", "credit_risk_score",
        "financial_risk_score", "operational_risk_score", "risk_tier"
    ]].sort_values(by="composite_risk_score", ascending=False)

    st.dataframe(
        display_df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "entity_id": st.column_config.TextColumn("Entity ID", width="small"),
            "entity_name": st.column_config.TextColumn("Counterparty Name", width="large"),
            "sector": st.column_config.TextColumn("Sector", width="medium"),
            "credit_rating": st.column_config.TextColumn("Rating", width="small"),
            "total_exposure_usd": st.column_config.NumberColumn("Exposure (USD)", format="$%d"),
            "expected_loss_usd": st.column_config.NumberColumn("Expected Loss", format="$%d"),
            "composite_risk_score": st.column_config.ProgressColumn("Composite ERS", format="%.1f", min_value=0, max_value=100),
            "credit_risk_score": st.column_config.NumberColumn("Credit", format="%.1f"),
            "financial_risk_score": st.column_config.NumberColumn("Liquidity", format="%.1f"),
            "operational_risk_score": st.column_config.NumberColumn("Ops", format="%.1f"),
            "risk_tier": st.column_config.TextColumn("Tier", width="small")
        }
    )


# ===========================================================================
# TAB 2: COUNTERPARTY DEEP-DIVE & ACTION PLAN
# ===========================================================================
with tab_entity:
    st.markdown("### 🔍 Counterparty Vulnerability Diagnostic & Decision Support")
    st.caption("Select an enterprise entity to inspect multi-pillar vulnerabilities, simulate credit tripwires, and generate prescriptive mitigation actions.")

    # Entity Selector Dropdown
    entity_options = df_scored["entity_id"] + " — " + df_scored["entity_name"] + " (" + df_scored["risk_tier"] + ")"
    # Default to first high-risk entity if available
    high_risk_indices = df_scored[df_scored["risk_tier"] == "High Risk"].index.tolist()
    default_idx = high_risk_indices[0] if high_risk_indices else 0

    selected_option = st.selectbox(
        "Select Enterprise Counterparty",
        options=entity_options,
        index=default_idx
    )
    selected_entity_id = selected_option.split(" — ")[0]
    entity_row = df_scored[df_scored["entity_id"] == selected_entity_id].iloc[0]

    # Two column layout: Entity Metrics & Spider Radar Chart
    c_diag1, c_diag2 = st.columns([1, 1])

    with c_diag1:
        tier = entity_row["risk_tier"]
        badge_cls = "badge-critical" if tier == "High Risk" else ("badge-medium" if tier == "Medium Risk" else "badge-low")
        st.markdown(f"#### {entity_row['entity_name']} <span class='{badge_cls}'>{tier}</span>", unsafe_allow_html=True)
        st.markdown(f"**Entity ID:** `{entity_row['entity_id']}` | **Sector:** {entity_row['sector']} | **Region:** {entity_row['jurisdiction']}")

        # Metric breakdown cards
        em1, em2, em3 = st.columns(3)
        with em1:
            st.metric("Composite Risk (ERS)", f"{entity_row['composite_risk_score']:.1f} / 100")
            st.metric("Current Ratio", f"{entity_row['current_ratio']:.2f}x")
            st.metric("Control Maturity", f"{entity_row['control_effectiveness_score']:.1f}%")
        with em2:
            st.metric("Credit Risk Score", f"{entity_row['credit_risk_score']:.1f} / 100")
            st.metric("Debt-to-Equity", f"{entity_row['debt_to_equity']:.2f}x")
            st.metric("Audit Findings", f"{entity_row['audit_findings_count']} issues")
        with em3:
            st.metric("Liquidity Risk Score", f"{entity_row['financial_risk_score']:.1f} / 100")
            st.metric("Interest Coverage", f"{entity_row['interest_coverage_ratio']:.2f}x")
            st.metric("SLA Breach Rate", f"{entity_row['sla_breach_rate']:.1%}")

        st.markdown(f"**Total Exposure at Default (EAD):** `${entity_row['total_exposure_usd']:,.2f}`")
        st.markdown(f"**Expected Loss (EL):** `${entity_row['expected_loss_usd']:,.2f}` (PD: `{entity_row['probability_of_default']:.2%}`, LGD: `{entity_row['loss_given_default']:.1%}`)")

    with c_diag2:
        st.plotly_chart(plot_entity_spider_radar(entity_row.to_dict()), use_container_width=True)

    st.markdown("---")

    # Prescriptive Action Plan & Decision Support
    st.markdown("#### 🎯 Prescriptive Decision Support & Action Plan")
    st.caption("Automated rule-based mitigation actions triggered by financial, operational, and credit threshold tripwires.")

    actions = generate_mitigation_actions(entity_row)
    for act in actions:
        p_cls = "critical" if act["priority"] == "Critical" else ("high" if act["priority"] == "High" else "medium")
        st.markdown(f"""
        <div class="mitigation-card {p_cls}">
            <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.4rem;">
                <strong style="color: #38BDF8; font-size: 1.05rem;">{act['category']} Trigger</strong>
                <span class="badge-{p_cls}">{act['priority']} Priority</span>
            </div>
            <div style="color: #CBD5E1; font-size: 0.92rem; margin-bottom: 0.5rem;">
                <strong>Tripwire:</strong> {act['trigger']}
            </div>
            <div style="color: #F8FAFC; font-weight: 500; font-size: 0.95rem; margin-bottom: 0.4rem;">
                <strong>Recommended Mitigation:</strong> {act['action']}
            </div>
            <div style="color: #94A3B8; font-size: 0.85rem;">
                ⏱️ <strong>Execution Window:</strong> {act['timeframe']} &nbsp;|&nbsp; 🛡️ <strong>Target Impact:</strong> {act['expected_impact']}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # Optional GenAI Qualitative Brief
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("#### 🧠 Executive AI Risk Briefing (Powered by Gemini)")
    st.caption("Synthesize a qualitative Board-level risk memo assessing strategic exposure and macroeconomic sensitivities.")

    ai_btn = st.button("Generate AI Risk Briefing Memo", key="btn_ai_brief")
    if ai_btn:
        with st.spinner("Analyzing counterparty telemetry and drafting executive memorandum..."):
            brief = generate_ai_risk_brief(
                entity_data=entity_row.to_dict(),
                api_key=api_key_input,
                model_name=gemini_model
            )
            st.info(brief)


# ===========================================================================
# TAB 3: STRATEGIC TRANSFORMATION ADVISOR
# ===========================================================================
with tab_strategic:
    st.markdown("### 🚀 Strategic Process Transformation & Digital Advisory")
    st.caption("AI-assisted workflow risk analysis, RACI governance matrix synthesis, and AS-IS vs TO-BE automation roadmap.")

    SAMPLE_PROCESS = """Our global organization is preparing to migrate core financial consolidation and procurement workflows from legacy on-premises ERP systems to a modernized Cloud ERP platform.

Current AS-IS Process Baseline:
1. Vendor Invoice Verification: Suppliers submit non-standard PDF invoices via email. AP staff manually key data into legacy ERP, leading to an average 4-day approval lag and a 3.8% manual entry error rate.
2. Intercompany Reconciliation: Month-end financial consolidation across 12 business units requires manual Excel workbook cross-referencing, demanding 140 staff hours per accounting close.
3. Procurement & Purchase Approvals: Purchase orders exceeding $50k undergo manual email sign-offs without central audit trail logging, resulting in a 7-day turnaround bottleneck.
4. Compliance & Controls Audit: Internal compliance reviews occur quarterly via retrospective sampling, exposing the firm to delayed regulatory audit penalties.

Target TO-BE Transformation Objectives:
- Implement automated document AI intelligence for 3-way matching and instant automated invoice capture.
- Automate multi-entity intercompany clearing with real-time continuous accounting ledger sync.
- Establish automated mobile-ready governance approval workflows with dynamic risk threshold limits.
- Deploy continuous automated control testing and continuous compliance monitoring."""

    process_input = st.text_area(
        "Enterprise Transformation Narrative / Process Specification",
        value=SAMPLE_PROCESS,
        height=240,
        help="Input your enterprise business process or migration architecture description."
    )

    if st.button("🚀 Synthesize Advisory Deliverables", key="btn_consulting"):
        if not api_key_input and not os.environ.get("GEMINI_API_KEY"):
            st.error("⚠️ Google Gemini API Key required. Please provide your key in the sidebar.")
        else:
            with st.spinner("Synthesizing Risk Register, RACI Matrix, and Gap Analysis via Gemini AI..."):
                try:
                    df_r, df_m, df_g = generate_consulting_suite(
                        process_description=process_input,
                        api_key=api_key_input,
                        model_name=gemini_model
                    )
                    st.session_state["suite_risk"] = df_r
                    st.session_state["suite_raci"] = df_m
                    st.session_state["suite_gap"] = df_g
                    st.success("✅ Transformation Advisory Suite generated successfully!")
                except Exception as e:
                    st.error(f"Error generating deliverables: {str(e)}")

    if "suite_risk" in st.session_state and "suite_raci" in st.session_state and "suite_gap" in st.session_state:
        st.markdown("<br>", unsafe_allow_html=True)
        t1, t2, t3 = st.tabs(["⚠️ Risk Register", "📋 RACI Governance", "⚡ AS-IS vs TO-BE Gap Analysis"])
        with t1:
            st.dataframe(st.session_state["suite_risk"], use_container_width=True, hide_index=True)
        with t2:
            st.dataframe(st.session_state["suite_raci"], use_container_width=True, hide_index=True)
        with t3:
            st.dataframe(st.session_state["suite_gap"], use_container_width=True, hide_index=True)


# ===========================================================================
# TAB 4: REPORTING & DATA CENTER
# ===========================================================================
with tab_data_export:
    st.markdown("### 📥 Executive Reporting & Data Management")
    st.caption("Generate multi-tab audit workbooks, export processed datasets, and manage synthetic data parameters.")

    col_exp1, col_exp2 = st.columns(2)

    with col_exp1:
        st.markdown("#### 📑 Executive Multi-Sheet Excel Report")
        st.write("Generates a formatted 4-sheet workbook (.xlsx) including:")
        st.markdown("""
        - **Sheet 1:** Executive Summary & Macro KPIs
        - **Sheet 2:** High-Risk Priority Watchlist
        - **Sheet 3:** Full Scored Counterparty Register
        - **Sheet 4:** Prescriptive Action Plan & Mitigation Triggers
        """)

        excel_data = generate_excel_risk_report(df_scored)
        st.download_button(
            label="📥 Download Executive Excel Report (.xlsx)",
            data=excel_data,
            file_name="Enterprise_Risk_Assessment_Report.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )

    with col_exp2:
        st.markdown("#### 💾 Raw & Processed Datasets")
        st.write("Download the current scored portfolio with calculated sub-scores and tiers in CSV format.")
        csv_bytes = df_scored.to_csv(index=False).encode("utf-8")
        st.download_button(
            label="📥 Download Scored Portfolio (.csv)",
            data=csv_bytes,
            file_name="enterprise_risk_portfolio_scored.csv",
            mime="text/csv",
            use_container_width=True
        )

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown("#### 🔄 Regenerate Synthetic Mock Dataset")
        st.write("Generate a fresh seed-controlled synthetic portfolio (500–1000 records).")
        num_gen = st.slider("Record Count", min_value=500, max_value=1000, value=750, step=50)
        seed_gen = st.number_input("Random Seed", min_value=1, max_value=9999, value=42)
        
        if st.button("Generate & Replace Dataset"):
            with st.spinner(f"Generating {num_gen} synthetic enterprise records..."):
                generate_synthetic_risk_data(
                    num_records=num_gen,
                    seed=seed_gen,
                    csv_path="data/enterprise_risk_dataset.csv",
                    sqlite_path="data/enterprise_risk.db"
                )
                st.cache_data.clear()
                st.success(f"Generated {num_gen} records and refreshed storage!")
                st.rerun()
