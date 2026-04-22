"""
Conversation Engine — Multi-turn GPT-4 conversation manager.

This is the brain of Phase 2. It:
  1. Maintains conversation history per session
  2. Sends the full history to GPT-4 with the conversation prompt
  3. Parses the AI's decision (ask_followup / confirm / complete)
  4. Handles edge cases (max turns, emergency keywords, etc.)

The AI NEVER diagnoses. It ONLY asks questions and structures data.
"""

import json
import logging
import os
from openai import OpenAI

from backend.prompts.conversation_prompt import get_conversation_prompt
from backend.session_store import Session
from backend.models.schemas import PatientSummary, Symptom, MedicalHistory

logger = logging.getLogger(__name__)


async def process_conversation_turn(session: Session, patient_text: str) -> dict:
    """
    Process a single turn in the multi-turn conversation.

    1. Add the patient's text to the session history
    2. Check if we should force confirmation (max turns reached)
    3. Send full history to GPT-4 with the conversation prompt
    4. Parse the AI's response and update session state
    5. Return the parsed response

    Args:
        session: The active Session object.
        patient_text: The patient's transcribed speech.

    Returns:
        dict with keys: action, ai_text, language, partial_summary, final_summary

    Raises:
        RuntimeError: If the GPT-4 API call fails.
    """
    # Add patient's message to history
    session.add_patient_turn(patient_text)

    logger.info(
        f"[Session {session.session_id[:8]}] "
        f"Turn {session.turn_count}: '{patient_text[:80]}...'"
    )

    # ── Build the messages array for GPT-4 ──
    messages = [
        {"role": "system", "content": get_conversation_prompt()}
    ]

    # Add conversation context about turn limits
    if session.should_force_confirm() and session.state == "asking":
        messages.append({
            "role": "system",
            "content": (
                "IMPORTANT: You have reached the maximum number of follow-up "
                "questions. You MUST now use action 'confirm' to confirm your "
                "understanding with the patient, even if some fields are missing. "
                "Use 'Not specified' for any missing fields."
            )
        })

    # Add all conversation history
    messages.extend(session.messages)

    try:
        client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            response_format={"type": "json_object"},
            temperature=0.3,  # Slightly higher than extraction for natural questions
            max_tokens=1024
        )

        raw_content = response.choices[0].message.content
        logger.debug(f"GPT-4 conversation response: {raw_content}")

        # Parse the response
        parsed = json.loads(raw_content)
        action = parsed.get("action", "ask_followup")

        # ── Handle each action type ──

        if action == "ask_followup":
            ai_text = parsed.get("question", "Could you tell me more?")
            language = parsed.get("language", "English")
            missing = parsed.get("missing_fields", [])

            # Record the AI's response in session
            session.add_ai_turn(ai_text)
            session.language = language
            session.state = "asking"

            logger.info(
                f"[Session {session.session_id[:8]}] "
                f"AI asks follow-up ({language}): '{ai_text[:60]}...' "
                f"Missing: {missing}"
            )

            return {
                "action": "ask_followup",
                "ai_text": ai_text,
                "language": language,
                "missing_fields": missing,
                "partial_summary": None,
                "final_summary": None,
            }

        elif action == "confirm":
            ai_text = parsed.get("confirmation_text", "Did I understand you correctly?")
            language = parsed.get("language", "English")
            partial = parsed.get("partial_summary", {})

            # Build partial summary
            partial_summary = _build_summary(partial)

            # Record in session
            session.add_ai_turn(ai_text)
            session.language = language
            session.state = "confirming"
            session.partial_summary = partial

            logger.info(
                f"[Session {session.session_id[:8]}] "
                f"AI confirms ({language}): '{ai_text[:60]}...'"
            )

            return {
                "action": "confirm",
                "ai_text": ai_text,
                "language": language,
                "missing_fields": [],
                "partial_summary": partial_summary,
                "final_summary": None,
            }

        elif action == "complete":
            summary_data = parsed.get("summary", {})
            final_summary = _build_summary(summary_data)

            # Mark session as complete
            session.state = "complete"
            session.final_summary = summary_data

            logger.info(
                f"[Session {session.session_id[:8]}] "
                f"Conversation complete! "
                f"{len(final_summary.symptoms)} symptoms, "
                f"severity={final_summary.severity}"
            )

            return {
                "action": "complete",
                "ai_text": "",
                "language": session.language,
                "missing_fields": [],
                "partial_summary": None,
                "final_summary": final_summary,
            }

        else:
            # Unknown action — treat as follow-up
            logger.warning(f"Unknown action '{action}', treating as follow-up")
            ai_text = parsed.get("question", parsed.get("text", "Could you tell me more?"))
            session.add_ai_turn(ai_text)

            return {
                "action": "ask_followup",
                "ai_text": ai_text,
                "language": session.language,
                "missing_fields": [],
                "partial_summary": None,
                "final_summary": None,
            }

    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse GPT-4 response: {e}")
        # Fallback: ask a generic follow-up
        fallback = "Could you tell me a bit more about how you're feeling?"
        session.add_ai_turn(fallback)
        return {
            "action": "ask_followup",
            "ai_text": fallback,
            "language": "English",
            "missing_fields": [],
            "partial_summary": None,
            "final_summary": None,
        }
    except Exception as e:
        logger.error(f"Conversation engine error: {e}")
        raise RuntimeError(f"Conversation processing failed: {str(e)}") from e


def _build_summary(data: dict) -> PatientSummary:
    """
    Build a PatientSummary from a raw dict (from GPT-4 response).
    Handles missing or malformed fields gracefully.
    """
    symptoms = [
        Symptom(
            name=s.get("name", "Unknown"),
            duration=s.get("duration", "Not specified"),
            details=s.get("details", "")
        )
        for s in data.get("symptoms", [])
    ]

    med_hist_data = data.get("medical_history", {})
    medical_history = MedicalHistory(
        chronic_conditions=med_hist_data.get("chronic_conditions", []),
        allergies=med_hist_data.get("allergies", [])
    ) if med_hist_data else None

    return PatientSummary(
        age=data.get("age", "Not specified"),
        symptoms=symptoms,
        medical_history=medical_history,
        severity=data.get("severity", "Not assessed"),
        chief_complaint=data.get("chief_complaint", "Not specified"),
        additional_notes=data.get("additional_notes", "")
    )
