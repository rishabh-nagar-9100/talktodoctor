"""
Medical intake API endpoint.

Accepts audio files from the patient kiosk, transcribes them
via Whisper, extracts structured data via GPT-4, and returns
the complete intake response.
"""

import logging
from typing import Optional
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException, Form

from backend.models.schemas import IntakeResponse, PatientSummary
from backend.services.transcription import transcribe_audio
from backend.services.extraction import extract_patient_summary

logger = logging.getLogger(__name__)
router = APIRouter()

from backend.db.supabase import get_db

# ──────────────────────────────────────────────
# Moved to Supabase DB
# ──────────────────────────────────────────────
intake_records: list[dict] = [] # Kept for backward compatibility with phase 1 POST


@router.post(
    "/intake",
    response_model=IntakeResponse,
    summary="Process patient audio intake",
    description=(
        "Accepts an audio file, transcribes it using Whisper, "
        "then extracts structured medical data using GPT-4. "
        "The AI does NOT diagnose — it only extracts and structures "
        "what the patient said."
    ),
)
async def process_intake(
    audio: UploadFile = File(..., description="Patient audio recording"),
    patient_id: Optional[str] = Form(None, description="Optional patient ID")
):
    """
    Main intake processing pipeline:
    1. Receive audio file
    2. Transcribe via Whisper
    3. Extract structured data via GPT-4
    4. Return IntakeResponse
    """
    logger.info(f"Received intake audio: {audio.filename} ({audio.content_type})")

    # ── Step 1: Read the audio file ──
    try:
        audio_bytes = await audio.read()
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Uploaded audio file is empty.")
        logger.info(f"Audio file size: {len(audio_bytes)} bytes")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to read audio file: {e}")
        raise HTTPException(status_code=400, detail=f"Failed to read audio file: {str(e)}")

    # ── Step 2: Transcribe audio via Whisper ──
    try:
        transcript = await transcribe_audio(audio_bytes, audio.filename)
        logger.info(f"Transcription result: '{transcript[:100]}...'")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Transcription error: {str(e)}")
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Transcription service error: {str(e)}")

    # ── Step 3: Extract structured data via GPT-4 ──
    try:
        summary = await extract_patient_summary(transcript)
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Extraction error: {str(e)}")
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Extraction service error: {str(e)}")

    # ── Step 4: Build response ──
    response = IntakeResponse(
        patient_id=patient_id,
        transcript=transcript,
        summary=summary
    )

    # Store in memory for the doctor dashboard to retrieve
    intake_records.append({
        "id": len(intake_records) + 1,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "data": response.model_dump()
    })

    logger.info(f"Intake processed successfully. Record #{len(intake_records)}")
    return response


@router.get(
    "/intake/latest",
    summary="Get the latest intake record",
    description="Returns the most recent patient intake for the doctor dashboard.",
)
async def get_latest_intake():
    """Return the most recent intake record for the doctor dashboard."""
    if not intake_records:
        raise HTTPException(status_code=404, detail="No intake records found.")
    return intake_records[-1]


@router.get(
    "/intake/all",
    summary="Get all intake records",
    description="Returns all patient intakes for the doctor dashboard.",
)
async def get_all_intakes():
    """Return all intake records, newest first, from Supabase."""
    db = get_db()
    try:
        # Fetch completed sessions with their summaries and conversation turns
        # Supabase Python client handles joins if foreign keys are set up
        res = db.table("intake_sessions").select(
            "id, completed_at, medical_summaries(*), conversation_turns(*)"
        ).eq("status", "completed").order("completed_at", desc=True).execute()
        
        sessions = res.data
        formatted_records = []
        
        for s in sessions:
            # Reconstruct the summary
            summary_data = {}
            if s.get("medical_summaries") and len(s["medical_summaries"]) > 0:
                ms = s["medical_summaries"][0]
                summary_data = {
                    "chief_complaint": ms.get("chief_complaint"),
                    "symptoms": ms.get("symptoms", []),
                    "medical_history": ms.get("medical_history", {}),
                    "severity": ms.get("severity"),
                    "urgency_level": ms.get("urgency_level", "general")
                }
                
            # Reconstruct transcript and history
            turns = sorted(s.get("conversation_turns", []), key=lambda x: x["turn_number"])
            history = [{"role": t["role"], "text": t["text_content"], "timestamp": t["created_at"]} for t in turns]
            transcript = " ".join([t["text_content"] for t in turns if t["role"] == "patient"])
            
            formatted_records.append({
                "id": s["id"],
                "timestamp": s["completed_at"],
                "data": {
                    "summary": summary_data,
                    "transcript": transcript,
                    "conversation_history": history,
                    "disclaimer": "This is an AI-generated summary. It is NOT a diagnosis. The treating physician must verify all information with the patient."
                }
            })
            
        return formatted_records
        
    except Exception as e:
        logger.error(f"Failed to fetch intakes from Supabase: {e}")
        # Fallback to memory for Phase 1 endpoints if needed
        return list(reversed(intake_records))
