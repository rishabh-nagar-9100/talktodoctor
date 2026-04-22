"""
Doctor Assist Service — Phase 3.

Uses GPT-4 to generate suggested follow-up questions for the doctor
based on the structured patient intake data.

Combines:
  - Deterministic risk assessment (from risk_calculator.py)
  - LLM-generated follow-up questions (from GPT-4)
  - Critical symptom flagging

The AI does NOT diagnose — it only suggests questions.
"""

import json
import logging
import os
from openai import OpenAI

from backend.prompts.followup_prompt import get_followup_prompt
from backend.services.risk_calculator import (
    calculate_risk_level,
    is_critical_symptom,
)
from backend.services.triage_engine import determine_triage_urgency

logger = logging.getLogger(__name__)


async def generate_doctor_analysis(summary: dict) -> dict:
    """
    Generate a complete doctor analysis package:
    1. Deterministic risk assessment
    2. Critical symptom flags
    3. LLM-generated follow-up questions

    Args:
        summary: A PatientSummary dict from the intake.

    Returns:
        dict with risk_assessment, critical_symptoms, followup_questions
    """
    # ── Step 1: Deterministic Risk Assessment ──
    risk = calculate_risk_level(summary)

    # ── Step 2: Flag Critical Symptoms ──
    symptoms = summary.get("symptoms", [])
    critical_symptoms = []
    for s in symptoms:
        name = s.get("name", "")
        if is_critical_symptom(name):
            critical_symptoms.append(name)

    # Also check details text for critical keywords
    for s in symptoms:
        details = s.get("details", "")
        if details and is_critical_symptom(details):
            if s.get("name", "") not in critical_symptoms:
                critical_symptoms.append(s.get("name", "Unknown"))

    # ── Step 3: LLM Follow-Up Questions ──
    followup_questions = await _generate_followup_questions(summary)

    # ── Step 4: Triage Engine ──
    triage = await determine_triage_urgency(summary)
    
    # Merge triage urgency into risk assessment for the frontend
    risk["urgency_level"] = triage.get("urgency_level", "Not Assessed")
    risk["triage_reasoning"] = triage.get("reasoning", "")

    return {
        "risk_assessment": risk,
        "critical_symptoms": critical_symptoms,
        "followup_questions": followup_questions,
    }


async def _generate_followup_questions(summary: dict) -> list[dict]:
    """
    Use GPT-4 to generate targeted follow-up questions for the doctor.

    Args:
        summary: A PatientSummary dict.

    Returns:
        List of question dicts with: question, category, priority, rationale
    """
    # Build a clean summary string for the LLM
    summary_text = _format_summary_for_llm(summary)

    if not summary_text.strip():
        return [{
            "question": "Please verify the patient's chief complaint.",
            "category": "General",
            "priority": "High",
            "rationale": "Insufficient data from intake for specific follow-up suggestions."
        }]

    try:
        client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": get_followup_prompt()},
                {"role": "user", "content": f"Patient Intake Summary:\n\n{summary_text}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.3,
            max_tokens=1024,
        )

        raw = response.choices[0].message.content
        parsed = json.loads(raw)

        questions = parsed.get("followup_questions", [])

        # Validate and clean
        validated = []
        for q in questions:
            validated.append({
                "question": q.get("question", ""),
                "category": q.get("category", "General"),
                "priority": q.get("priority", "Medium"),
                "rationale": q.get("rationale", ""),
            })

        logger.info(f"Generated {len(validated)} follow-up questions for doctor")
        return validated

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse follow-up questions JSON: {e}")
        return [{
            "question": "Please conduct a standard symptom review with the patient.",
            "category": "General",
            "priority": "Medium",
            "rationale": "AI follow-up generation encountered an error.",
        }]
    except Exception as e:
        logger.error(f"Follow-up question generation error: {e}")
        return [{
            "question": "Please conduct a standard symptom review with the patient.",
            "category": "General",
            "priority": "Medium",
            "rationale": f"AI follow-up generation unavailable: {str(e)[:80]}",
        }]


def _format_summary_for_llm(summary: dict) -> str:
    """Format a PatientSummary dict into a readable string for the LLM."""
    lines = []

    age = summary.get("age", "Not specified")
    if age and age != "Not specified":
        lines.append(f"Age: {age}")

    chief = summary.get("chief_complaint", "Not specified")
    if chief and chief != "Not specified":
        lines.append(f"Chief Complaint: {chief}")

    severity = summary.get("severity", "Not assessed")
    lines.append(f"Severity: {severity}")

    symptoms = summary.get("symptoms", [])
    if symptoms:
        lines.append("\nSymptoms:")
        for s in symptoms:
            name = s.get("name", "Unknown")
            duration = s.get("duration", "Not specified")
            details = s.get("details", "")
            line = f"  - {name} (Duration: {duration})"
            if details:
                line += f" — {details}"
            lines.append(line)

    notes = summary.get("additional_notes", "")
    if notes:
        lines.append(f"\nAdditional Notes: {notes}")

    return "\n".join(lines)
