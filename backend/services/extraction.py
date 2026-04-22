"""
GPT-4 structured data extraction service.

Takes a raw patient transcript and uses GPT-4 with a carefully
crafted system prompt to extract structured medical intake data.
Uses JSON mode for reliable, parseable output.
"""

import json
import logging
import os
from openai import OpenAI

from backend.prompts.system_prompt import get_system_prompt
from backend.models.schemas import PatientSummary, Symptom, MedicalHistory

logger = logging.getLogger(__name__)


async def extract_patient_summary(transcript: str) -> PatientSummary:
    """
    Extract a structured patient summary from a raw transcript using GPT-4.

    The AI will NEVER diagnose — it only extracts and structures information
    that the patient explicitly stated.

    Args:
        transcript: Raw transcription text from Whisper.

    Returns:
        A PatientSummary object with structured symptom data.

    Raises:
        ValueError: If the transcript is empty or the AI response is invalid.
        RuntimeError: If the GPT-4 API call fails.
    """
    if not transcript or not transcript.strip():
        raise ValueError("Transcript is empty. Cannot extract summary.")

    logger.info(f"Extracting patient summary from transcript ({len(transcript)} chars)")

    try:
        client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {
                    "role": "system",
                    "content": get_system_prompt()
                },
                {
                    "role": "user",
                    "content": f"Patient statement:\n\n{transcript}"
                }
            ],
            response_format={"type": "json_object"},
            temperature=0.1,  # Low temperature for consistent, factual extraction
            max_tokens=1024
        )

        raw_content = response.choices[0].message.content
        logger.debug(f"GPT-4 raw response: {raw_content}")

        # Parse the JSON response
        parsed = json.loads(raw_content)

        # Build the PatientSummary from parsed data
        symptoms = [
            Symptom(
                name=s.get("name", "Unknown"),
                duration=s.get("duration", "Not specified"),
                details=s.get("details", "")
            )
            for s in parsed.get("symptoms", [])
        ]

        med_hist_data = parsed.get("medical_history", {})
        medical_history = MedicalHistory(
            chronic_conditions=med_hist_data.get("chronic_conditions", []),
            allergies=med_hist_data.get("allergies", [])
        ) if med_hist_data else None

        summary = PatientSummary(
            age=parsed.get("age", "Not specified"),
            symptoms=symptoms,
            medical_history=medical_history,
            severity=parsed.get("severity", "Not assessed"),
            chief_complaint=parsed.get("chief_complaint", "Not specified"),
            additional_notes=parsed.get("additional_notes", "")
        )

        logger.info(
            f"Extraction complete: {len(symptoms)} symptoms found, "
            f"severity={summary.severity}"
        )
        return summary

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GPT-4 response as JSON: {e}")
        raise ValueError(f"AI returned invalid JSON: {str(e)}") from e
    except Exception as e:
        logger.error(f"GPT-4 API error: {e}")
        raise RuntimeError(f"Extraction failed: {str(e)}") from e
