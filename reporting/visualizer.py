"""
visualizer.py
=============
Modern executive interactive visualizations using Plotly.
Includes tier distributions, risk vs exposure scatter, sector breakdowns,
and single-entity radar diagnostics.
"""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from typing import Dict, Any


TIER_COLORS = {
    "Low Risk": "#10B981",     # Emerald
    "Medium Risk": "#F59E0B",  # Amber
    "High Risk": "#EF4444"     # Ruby Red
}

DARK_TEMPLATE = "plotly_dark"


def plot_risk_tier_distribution(df: pd.DataFrame) -> go.Figure:
    """
    Renders an executive donut chart of portfolio entity distribution by risk tier.
    """
    counts = df["risk_tier"].value_counts().reset_index()
    counts.columns = ["Tier", "Count"]

    fig = px.pie(
        counts,
        names="Tier",
        values="Count",
        hole=0.55,
        color="Tier",
        color_discrete_map=TIER_COLORS,
        title="Portfolio Counterparties by Risk Tier"
    )
    fig.update_layout(
        template=DARK_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(l=20, r=20, t=50, b=30),
        font=dict(family="Inter, sans-serif")
    )
    fig.update_traces(
        textposition="inside",
        textinfo="percent+label",
        marker=dict(line=dict(color="#0F172A", width=2))
    )
    return fig


def plot_exposure_vs_risk(df: pd.DataFrame) -> go.Figure:
    """
    Renders an interactive scatter plot showing Total Exposure ($M) vs Composite Risk Score.
    Bubble size represents Expected Loss ($M).
    """
    df_plot = df.copy()
    df_plot["exposure_millions"] = df_plot["total_exposure_usd"] / 1_000_000.0
    df_plot["loss_millions"] = df_plot["expected_loss_usd"] / 1_000_000.0

    fig = px.scatter(
        df_plot,
        x="composite_risk_score",
        y="exposure_millions",
        color="risk_tier",
        size="loss_millions",
        size_max=35,
        hover_name="entity_name",
        hover_data={
            "entity_id": True,
            "sector": True,
            "credit_rating": True,
            "composite_risk_score": ":.1f",
            "exposure_millions": ":.2f",
            "loss_millions": ":.2f",
            "risk_tier": False
        },
        color_discrete_map=TIER_COLORS,
        labels={
            "composite_risk_score": "Composite Enterprise Risk Score (0-100)",
            "exposure_millions": "Exposure at Default (EAD, $ Millions)",
            "risk_tier": "Risk Tier"
        },
        title="Portfolio Exposure vs. Composite Risk Profile"
    )

    # Add vertical reference lines for thresholds
    fig.add_vline(x=35.0, line_dash="dash", line_color="#F59E0B", opacity=0.6, annotation_text="Medium Tier")
    fig.add_vline(x=65.0, line_dash="dash", line_color="#EF4444", opacity=0.6, annotation_text="High Risk Tier")

    fig.update_layout(
        template=DARK_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30, 41, 59, 0.4)",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        margin=dict(l=20, r=20, t=60, b=30),
        font=dict(family="Inter, sans-serif")
    )
    return fig


def plot_sector_risk_breakdown(df: pd.DataFrame) -> go.Figure:
    """
    Renders horizontal bar charts comparing Average Risk Score across sectors.
    """
    sector_summary = df.groupby("sector").agg(
        avg_score=("composite_risk_score", "mean"),
        total_exp=("total_exposure_usd", "sum"),
        entity_count=("entity_id", "count")
    ).reset_index().sort_values(by="avg_score", ascending=True)

    fig = px.bar(
        sector_summary,
        x="avg_score",
        y="sector",
        orientation="h",
        color="avg_score",
        color_continuous_scale="Viridis_r",
        labels={"avg_score": "Mean Risk Score (0-100)", "sector": "Industry Sector"},
        title="Industry Sector Risk Index Benchmark"
    )
    fig.update_layout(
        template=DARK_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(30, 41, 59, 0.4)",
        coloraxis_showscale=False,
        margin=dict(l=20, r=20, t=50, b=30),
        font=dict(family="Inter, sans-serif")
    )
    return fig


def plot_entity_spider_radar(entity_data: Dict[str, Any]) -> go.Figure:
    """
    Renders a 5-pillar radar/spider chart for a deep-dive assessment of a single entity.
    """
    categories = [
        "Credit Risk",
        "Financial Distress",
        "Operational Risk",
        "Leverage Severity",
        "Compliance Gap"
    ]
    
    # Calculate normalized dimensions (0 - 100 scale)
    credit = float(entity_data.get("credit_risk_score", 50.0))
    financial = float(entity_data.get("financial_risk_score", 50.0))
    operational = float(entity_data.get("operational_risk_score", 50.0))
    
    de = float(entity_data.get("debt_to_equity", 1.0))
    leverage = min(100.0, (de / 5.0) * 100.0)
    
    compliance = float(entity_data.get("regulatory_compliance_score", 80.0))
    comp_gap = max(0.0, 100.0 - compliance)

    values = [credit, financial, operational, leverage, comp_gap]
    # Close the loop
    values_closed = values + [values[0]]
    categories_closed = categories + [categories[0]]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values_closed,
        theta=categories_closed,
        fill='toself',
        fillcolor='rgba(56, 189, 248, 0.25)',
        line=dict(color='#38BDF8', width=2.5),
        name=entity_data.get("entity_name", "Entity")
    ))

    fig.update_layout(
        polar=dict(
            radialaxis=dict(
                visible=True,
                range=[0, 100],
                gridcolor="rgba(255, 255, 255, 0.15)",
                linecolor="rgba(255, 255, 255, 0.15)",
                tickfont=dict(size=9, color="#94A3B8")
            ),
            angularaxis=dict(
                gridcolor="rgba(255, 255, 255, 0.15)",
                linecolor="rgba(255, 255, 255, 0.15)",
                tickfont=dict(size=11, color="#F1F5F9")
            ),
            bgcolor="rgba(30, 41, 59, 0.5)"
        ),
        template=DARK_TEMPLATE,
        paper_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=40, r=40, t=40, b=40),
        title=f"Multi-Pillar Risk Radar: {entity_data.get('entity_name', '')}",
        font=dict(family="Inter, sans-serif")
    )
    return fig
