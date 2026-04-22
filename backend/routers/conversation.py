"""
Conversation API endpoints (Phase 2).

Manages multi-turn patient intake conversations:
  - POST /conversation/start   — Begin a new session
  - POST /conversation/respond — Send patient audio, get AI response
  - GET  /conversation/{id}    — Get session state

The Phase 1 /intake endpoint remains untouched for backward compatibility.
"""

import logging
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from backend.models.schemas import (
    ConversationStartResponse,
    ConversationResponse,
    ConversationAction,
    ConversationTurn,
)
from backend.session_store import session_store
from backend.services.transcription import transcribe_audio
from backend.services.conversation_engine import process_conversation_turn
from backend.services.tts import generate_speech
from backend.prompts.conversation_prompt import get_initial_question
from backend.db.supabase import get_db

# Import removed since we use Supabase

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/conversation/start",
    response_model=ConversationStartResponse,
    summary="Start a new intake conversation",
    description=(
        "Creates a new conversation session and returns the AI's "
        "opening question with TTS audio. The patient should hear "
        "this question and then respond."
    ),
)
async def start_conversation(language: str = Form("English")):
    """
    Begin a new multi-turn intake conversation.

    1. Create a session
    2. Generate the opening question in the specified language
    3. Generate TTS audio for the question
    4. Return session_id + question + audio
    """
    # Create a new session
    session = await session_store.create_session()
    session.language = language
    logger.info(f"New conversation started: {session.session_id} in {language}")

    # Get the initial question
    initial_question = get_initial_question(language)
    session.add_ai_turn(initial_question)

    # Database Insert: Create Intake Session
    try:
        db = get_db()
        db.table("intake_sessions").insert({
            "id": session.session_id,
            "language": language,
            "status": "in_progress"
        }).execute()
        
        # Insert initial AI turn
        db.table("conversation_turns").insert({
            "session_id": session.session_id,
            "turn_number": 1,
            "role": "ai",
            "text_content": initial_question
        }).execute()
    except Exception as e:
        logger.error(f"Failed to insert session into DB: {e}")

    # Generate TTS for the opening question
    audio_base64 = None
    try:
        audio_base64 = await generate_speech(initial_question)
        session.tts_audio[1] = audio_base64
    except Exception as e:
        logger.warning(f"TTS generation failed for opening question: {e}")
        # Continue without audio — the frontend will show text instead

    return ConversationStartResponse(
        session_id=session.session_id,
        ai_question=initial_question,
        audio_base64=audio_base64,
        turn_number=1,
        action="ask_followup",
    )


@router.post(
    "/conversation/respond",
    response_model=ConversationResponse,
    summary="Send patient response in the conversation",
    description=(
        "Accepts patient audio for the current conversation turn. "
        "Transcribes via Whisper, processes through the conversation "
        "engine, and returns the AI's next action (follow-up, confirm, "
        "or complete) with optional TTS audio."
    ),
)
async def respond_in_conversation(
    audio: UploadFile = File(..., description="Patient audio recording"),
    session_id: str = Form(..., description="Active session ID"),
):
    """
    Process a patient's audio response in the conversation.

    1. Fetch the session
    2. Transcribe the audio
    3. Run the conversation engine
    4. Generate TTS if the AI has a follow-up
    5. If complete, store in intake_records for the doctor dashboard
    6. Return the response
    """
    # ── Step 1: Get the session ──
    session = await session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired. Please start a new conversation."
        )

    if session.state == "complete":
        raise HTTPException(
            status_code=400,
            detail="This conversation is already complete."
        )

    # ── Step 2: Read and transcribe audio ──
    try:
        audio_bytes = await audio.read()
        if len(audio_bytes) == 0:
            raise HTTPException(status_code=400, detail="Audio file is empty.")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to read audio: {str(e)}")

    try:
        transcript = await transcribe_audio(audio_bytes, audio.filename)
        logger.info(f"[Session {session_id[:8]}] Patient said: '{transcript[:80]}'")
    except ValueError as e:
        raise HTTPException(status_code=422, detail=f"Transcription error: {str(e)}")
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Transcription service error: {str(e)}")

    # ── Step 3: Process through conversation engine ──
    try:
        result = await process_conversation_turn(session, transcript)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"Conversation engine error: {str(e)}")

    action = result["action"]
    ai_text = result["ai_text"]

    # Database Insert: Save patient transcript and AI response
    try:
        db = get_db()
        # Patient turn
        db.table("conversation_turns").insert({
            "session_id": session_id,
            "turn_number": session.turn_count,
            "role": "patient",
            "text_content": transcript
        }).execute()

        # AI turn (if there is a response)
        if ai_text:
            db.table("conversation_turns").insert({
                "session_id": session_id,
                "turn_number": session.turn_count + 1,
                "role": "ai",
                "text_content": ai_text
            }).execute()
    except Exception as e:
        logger.error(f"Failed to insert turns to DB: {e}")

    # ── Step 4: Generate TTS for AI response (if not complete) ──
    audio_base64 = None
    if ai_text and action != "complete":
        try:
            audio_base64 = await generate_speech(ai_text)
            session.tts_audio[session.turn_count + 1] = audio_base64
        except Exception as e:
            logger.warning(f"TTS generation failed: {e}")
            # Continue without audio

    # ── Step 5: If complete, store for doctor dashboard ──
    created_intake_id = None
    if action == "complete" and result["final_summary"]:
        # We use the session_id as the intake_id now
        created_intake_id = session_id
        
        try:
            db = get_db()
            summary = result["final_summary"]
            
            # Update session status
            db.table("intake_sessions").update({
                "status": "completed",
                "completed_at": datetime.now(timezone.utc).isoformat()
            }).eq("id", session_id).execute()
            
            # Insert medical summary
            db.table("medical_summaries").insert({
                "session_id": session_id,
                "chief_complaint": summary.chief_complaint,
                "symptoms": [s.model_dump() for s in summary.symptoms],
                "medical_history": summary.medical_history.model_dump() if summary.medical_history else {},
                "severity": summary.severity,
                "urgency_level": summary.urgency_level
            }).execute()
            
            logger.info(f"[Session {session_id[:8]}] Conversation complete, saved to Supabase.")
        except Exception as e:
            logger.error(f"Failed to finalize session in DB: {e}")

    # ── Step 6: Build response ──
    conversation_history = [
        ConversationTurn(role=t["role"], text=t["text"], timestamp=t["timestamp"])
        for t in session.turns
    ]

    return ConversationResponse(
        session_id=session_id,
        action=ConversationAction(action),
        ai_text=ai_text,
        audio_base64=audio_base64,
        patient_transcript=transcript,
        turn_number=session.turn_count,
        language=result.get("language", session.language),
        partial_summary=result.get("partial_summary"),
        final_summary=result.get("final_summary"),
        conversation_history=conversation_history,
        intake_id=created_intake_id,
    )


@router.get(
    "/conversation/{session_id}",
    summary="Get conversation session state",
    description="Returns the current state and history of a conversation session.",
)
async def get_conversation(session_id: str):
    """Return the current state of a conversation session."""
    session = await session_store.get_session(session_id)
    if session is None:
        raise HTTPException(
            status_code=404,
            detail="Session not found or expired."
        )

    return {
        "session_id": session.session_id,
        "state": session.state,
        "turn_count": session.turn_count,
        "language": session.language,
        "turns": session.turns,
        "partial_summary": session.partial_summary,
        "final_summary": session.final_summary,
    }


def _build_full_transcript(session) -> str:
    """
    Build a single transcript string from all patient turns
    for the doctor dashboard.
    """
    patient_turns = [t["text"] for t in session.turns if t["role"] == "patient"]
    return " ".join(patient_turns)
