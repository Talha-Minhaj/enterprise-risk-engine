"""
consulting_suite.py
===================
Enterprise Digital Transformation & Process Risk Advisory Suite.
Generates structured Risk Register, RACI Governance Matrix, and AS-IS/TO-BE Gap Analysis
using modern Google Gemini API (google-genai) with strict Pydantic structured schemas.
Fully sanitized for public portfolio showcase.
"""

import os
import json
import re
import pandas as pd
from typing import List, Optional, Tuple, Dict, Any
from pydantic import BaseModel, Field

# Check modern google-genai SDK
try:
    from google import genai
    from google.genai import types
    HAS_GENAI_SDK = True
except ImportError:
    HAS_GENAI_SDK = False

try:
    import google.generativeai as legacy_genai
    HAS_LEGACY_SDK = True
except ImportError:
    HAS_LEGACY_SDK = False


# ---------------------------------------------------------------------------
# Pydantic Schemas for Structured JSON Generation
# ---------------------------------------------------------------------------

class RiskItem(BaseModel):
    risk_id: str = Field(description="Unique risk code, e.g., RSK-001")
    description: str = Field(description="Detailed assessment of process or architectural risk")
    severity: str = Field(description="Severity classification: High, Medium, or Low")
    mitigation_strategy: str = Field(description="Actionable enterprise mitigation plan")


class RaciItem(BaseModel):
    task_name: str = Field(description="Process task or transformation milestone")
    responsible: str = Field(description="Role responsible for executing work (Doers)")
    accountable: str = Field(description="Role accountable for final delivery (Owner)")
    consulted: str = Field(description="Roles consulted for expert input")
    informed: str = Field(description="Roles kept informed of milestones")


class GapAnalysisItem(BaseModel):
    as_is_step: str = Field(description="Current baseline process step (AS-IS)")
    bottleneck: str = Field(description="Key inefficiency, manual delay, or risk point")
    to_be_automation: str = Field(description="Target automated solution (TO-BE)")
    estimated_time_savings: str = Field(description="Quantified efficiency gain (e.g., '75% time reduction')")


class ConsultingSuiteOutput(BaseModel):
    risk_register: List[RiskItem] = Field(description="Comprehensive Risk Register array")
    raci_matrix: List[RaciItem] = Field(description="RACI Governance Matrix array")
    gap_analysis: List[GapAnalysisItem] = Field(description="AS-IS vs TO-BE Gap Analysis array")


SYSTEM_PROMPT = """
You are a Principal Enterprise Risk & Process Transformation Consultant.
Your objective is to analyze enterprise business process descriptions (e.g., core system migrations, financial workflows, procurement cycles, supply chain automations) and produce high-value, structured advisory deliverables.

Analyze the user's process input thoroughly and synthesize 3 structured consulting artifacts:
1. Risk Register: Identify key operational, technical, financial, governance, and organizational risks.
2. RACI Matrix: Define a clear governance framework mapping critical project tasks to enterprise roles (e.g., Enterprise Architect, Risk Lead, Process Owner, Change Manager, Systems Engineer).
3. AS-IS vs TO-BE Gap Analysis: Map baseline friction points directly to next-generation automated future states, with realistic quantified time/cost savings.

Provide realistic, specific, and professional enterprise risk management output.
"""


def _extract_json_from_response(text: str) -> Dict[str, Any]:
    """Extract and parse JSON object from model raw text response, cleaning markdown fences."""
    text_str = text.strip()
    if "```json" in text_str:
        text_str = re.sub(r"^```json\s*", "", text_str, flags=re.MULTILINE)
        text_str = re.sub(r"```$", "", text_str, flags=re.MULTILINE).strip()
    elif "```" in text_str:
        text_str = re.sub(r"^```\s*", "", text_str, flags=re.MULTILINE)
        text_str = re.sub(r"```$", "", text_str, flags=re.MULTILINE).strip()

    first_brace = text_str.find("{")
    last_brace = text_str.rfind("}")
    if first_brace != -1 and last_brace != -1:
        text_str = text_str[first_brace:last_brace + 1]

    return json.loads(text_str)


def generate_consulting_suite(
    process_description: str,
    api_key: Optional[str] = None,
    model_name: str = "gemini-2.5-flash"
) -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """
    Generates strategic transformation risk deliverables using Google Gemini API.

    Parameters:
        process_description (str): Detailed baseline enterprise process input.
        api_key (str, optional): Google Gemini API Key.
        model_name (str): Gemini model identifier (default: 'gemini-2.5-flash').

    Returns:
        Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]: (df_risk, df_raci, df_gap)
    """
    effective_api_key = api_key or os.environ.get("GEMINI_API_KEY")
    if not effective_api_key:
        raise ValueError(
            "Gemini API Key is missing. Please set the GEMINI_API_KEY environment variable or enter it in the interface."
        )

    if not process_description or not process_description.strip():
        raise ValueError("Process description cannot be empty.")

    prompt_content = f"{SYSTEM_PROMPT}\n\nPROCESS DESCRIPTION FOR ANALYSIS:\n{process_description.strip()}"
    raw_json_dict = None

    if HAS_GENAI_SDK:
        client = genai.Client(api_key=effective_api_key)
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=ConsultingSuiteOutput,
            temperature=0.2,
        )
        response = client.models.generate_content(
            model=model_name,
            contents=prompt_content,
            config=config,
        )
        if not response.text:
            raise RuntimeError("Gemini API returned an empty response.")
        raw_json_dict = _extract_json_from_response(response.text)

    elif HAS_LEGACY_SDK:
        legacy_genai.configure(api_key=effective_api_key)
        model = legacy_genai.GenerativeModel("gemini-1.5-flash")
        json_prompt = (
            f"{prompt_content}\n\n"
            "Output MUST be strict JSON matching this structure:\n"
            "{\n"
            '  "risk_register": [{"risk_id": "RSK-001", "description": "...", "severity": "High", "mitigation_strategy": "..."}],\n'
            '  "raci_matrix": [{"task_name": "...", "responsible": "...", "accountable": "...", "consulted": "...", "informed": "..."}],\n'
            '  "gap_analysis": [{"as_is_step": "...", "bottleneck": "...", "to_be_automation": "...", "estimated_time_savings": "..."}]\n'
            "}"
        )
        response = model.generate_content(json_prompt)
        raw_json_dict = _extract_json_from_response(response.text)
    else:
        raise ImportError("google-genai python package is required. Install via `pip install google-genai`.")

    if not isinstance(raw_json_dict, dict):
        raise ValueError("Invalid response format received from model.")

    risk_list = raw_json_dict.get("risk_register", [])
    raci_list = raw_json_dict.get("raci_matrix", [])
    gap_list = raw_json_dict.get("gap_analysis", [])

    df_risk = pd.DataFrame(risk_list)
    df_raci = pd.DataFrame(raci_list)
    df_gap = pd.DataFrame(gap_list)

    if df_risk.empty:
        df_risk = pd.DataFrame(columns=["Risk ID", "Description", "Severity", "Mitigation Strategy"])
    else:
        cols = [c for c in ["risk_id", "description", "severity", "mitigation_strategy"] if c in df_risk.columns]
        df_risk = df_risk[cols]
        df_risk.rename(columns={
            "risk_id": "Risk ID",
            "description": "Description",
            "severity": "Severity",
            "mitigation_strategy": "Mitigation Strategy"
        }, inplace=True)

    if df_raci.empty:
        df_raci = pd.DataFrame(columns=["Task Name", "Responsible (R)", "Accountable (A)", "Consulted (C)", "Informed (I)"])
    else:
        cols = [c for c in ["task_name", "responsible", "accountable", "consulted", "informed"] if c in df_raci.columns]
        df_raci = df_raci[cols]
        df_raci.rename(columns={
            "task_name": "Task Name",
            "responsible": "Responsible (R)",
            "accountable": "Accountable (A)",
            "consulted": "Consulted (C)",
            "informed": "Informed (I)"
        }, inplace=True)

    if df_gap.empty:
        df_gap = pd.DataFrame(columns=["AS-IS Process Step", "Identified Bottleneck", "TO-BE Solution", "Estimated Savings"])
    else:
        cols = [c for c in ["as_is_step", "bottleneck", "to_be_automation", "estimated_time_savings"] if c in df_gap.columns]
        df_gap = df_gap[cols]
        df_gap.rename(columns={
            "as_is_step": "AS-IS Process Step",
            "bottleneck": "Identified Bottleneck",
            "to_be_automation": "TO-BE Solution",
            "estimated_time_savings": "Estimated Savings"
        }, inplace=True)

    return df_risk, df_raci, df_gap
