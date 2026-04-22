"""
Doctor-facing API endpoints — Phase 3.

Provides clinical intelligence endpoints for the doctor dashboard:
  - POST /doctor/analyze/{intake_id}  — Get risk + follow-up questions
  - GET  /doctor/risk-keywords        — List critical symptom keywords

The AI NEVER diagnoses. These are decision-support tools only.
"""

import logging
from fastapi import APIRouter, HTTPException

from backend.db.supabase import get_db
from backend.services.doctor_assist import generate_doctor_analysis
from backend.services.risk_calculator import (
    calculate_risk_level,
    get_critical_keywords,
)

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/doctor/analyze/{intake_id}",
    summary="Generate doctor analysis for an intake",
    description=(
        "Takes an existing intake record and generates: "
        "1) Deterministic risk assessment, "
        "2) Critical symptom flags, "
        "3) AI-suggested follow-up questions. "
        "The risk level is calculated WITHOUT an LLM for deterministic safety."
    ),
)
async def analyze_intake(intake_id: str):
    """
    Generate a full doctor analysis package for a given intake ID.
    """
    db = get_db()
    res = db.table("medical_summaries").select("*").eq("session_id", intake_id).execute()
    
    if not res.data:
        raise HTTPException(status_code=404, detail=f"Intake summary #{intake_id} not found.")

    # The downstream services (calculate_risk_level, generate_doctor_analysis)
    # expect a plain dict with .get() access, which matches the Supabase row format.
    summary = res.data[0]

    logger.info(f"Generating doctor analysis for intake #{intake_id}")

    try:
        analysis = await generate_doctor_analysis(summary)
    except Exception as e:
        logger.error(f"Doctor analysis failed: {e}")
        # Return deterministic risk even if LLM fails
        risk = calculate_risk_level(summary)
        analysis = {
            "risk_assessment": risk,
            "critical_symptoms": [],
            "followup_questions": [{
                "question": "Please conduct a standard symptom review.",
                "category": "General",
                "priority": "Medium",
                "rationale": "AI follow-up generation was unavailable.",
            }],
        }

    return {
        "intake_id": intake_id,
        "analysis": analysis,
        "disclaimer": (
            "This analysis is AI-generated and is NOT a diagnosis. "
            "The risk level is a triage priority hint only. "
            "The treating physician is the final authority."
        ),
    }


@router.get(
    "/doctor/risk-keywords",
    summary="Get critical symptom keywords",
    description=(
        "Returns the list of keywords used by the deterministic "
        "risk calculator to flag critical symptoms."
    ),
)
async def get_risk_keywords():
    """Return the critical keyword list (useful for frontend highlighting)."""
    return {
        "critical_keywords": get_critical_keywords(),
        "note": (
            "These keywords are used for deterministic risk flagging. "
            "Presence of any critical keyword automatically triggers a High risk level."
        ),
    }
