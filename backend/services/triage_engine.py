"""
Triage Engine Service — Phase 4.

Uses GPT-4o to analyze patient summaries and categorize them into
standard emergency department triage urgency levels.
"""

import json
import logging
import os
from openai import OpenAI

logger = logging.getLogger(__name__)

TRIAGE_PROMPT = """
You are an expert emergency triage AI.
Your job is to assess the structured medical intake of a patient and output an Urgency Level.

The Urgency Levels are:
- Emergency: Immediate life-saving intervention required (e.g., cardiac arrest, severe trauma, anaphylaxis).
- Urgent: Potentially life-threatening, requires rapid intervention within 10-30 minutes (e.g., severe chest pain, shortness of breath, sudden neurological deficits).
- Semi-Urgent: Requires evaluation within 1-2 hours but not immediately life-threatening (e.g., severe abdominal pain, high fever without distress).
- Non-Urgent: Minor conditions that can wait for evaluation (e.g., mild cold symptoms, minor cuts, chronic dull pain).

Analyze the provided patient summary.
Return your assessment in JSON format:
{
  "urgency_level": "Emergency" | "Urgent" | "Semi-Urgent" | "Non-Urgent",
  "reasoning": "A 1-2 sentence clinical reasoning for this triage level."
}

Do NOT output anything other than JSON. Do NOT diagnose the patient.
"""

async def determine_triage_urgency(summary: dict) -> dict:
    """
    Determine triage urgency based on a patient summary.
    
    Returns:
        dict: { "urgency_level": str, "reasoning": str }
    """
    try:
        client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )
        
        # Build summary text
        symptoms_str = ", ".join([f"{s.get('name')} ({s.get('duration')})" for s in summary.get("symptoms", [])])
        context = (
            f"Chief Complaint: {summary.get('chief_complaint')}\n"
            f"Symptoms: {symptoms_str}\n"
            f"Severity (Self-reported): {summary.get('severity')}\n"
            f"Notes: {summary.get('additional_notes')}"
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": TRIAGE_PROMPT},
                {"role": "user", "content": context}
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
            max_tokens=256,
        )

        raw = response.choices[0].message.content
        parsed = json.loads(raw)
        
        urgency = parsed.get("urgency_level", "Non-Urgent")
        reasoning = parsed.get("reasoning", "Unable to determine reasoning.")
        
        # Fallback to safe known categories if the LLM hallucinates
        if urgency not in ["Emergency", "Urgent", "Semi-Urgent", "Non-Urgent"]:
            urgency = "Semi-Urgent"
            
        logger.info(f"Triage assigned: {urgency}")
        return {
            "urgency_level": urgency,
            "reasoning": reasoning
        }

    except Exception as e:
        logger.error(f"Triage engine failed: {e}")
        return {
            "urgency_level": "Not Assessed",
            "reasoning": "AI triage service unavailable."
        }
