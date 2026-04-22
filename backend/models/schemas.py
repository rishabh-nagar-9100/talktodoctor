"""
Pydantic models for the medical intake API.

Defines the structured data shapes for:
- Phase 1: Symptoms, patient summaries, and intake responses
- Phase 2: Conversation turns, sessions, and conversation responses

These models enforce validation and provide clear documentation
of the API contract.
"""

from enum import Enum
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone


# ══════════════════════════════════════════════
#  Phase 4 — Patient & Report Models
# ══════════════════════════════════════════════

class Patient(BaseModel):
    """Patient demographics."""
    id: str = Field(..., description="Unique patient identifier")
    name: str = Field(..., description="Patient's full name")
    age: int = Field(..., description="Patient's age")
    gender: str = Field(..., description="Patient's gender")
    created_at: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When the patient was registered"
    )

class MedicalReport(BaseModel):
    """Structured data extracted from an uploaded medical report (e.g. X-ray, lab)."""
    id: str = Field(..., description="Unique report identifier")
    patient_id: str = Field(..., description="Linked patient identifier")
    report_type: str = Field(..., description="Type of report (e.g., 'Chest X-ray', 'Blood Test')")
    findings: List[str] = Field(default_factory=list, description="Key findings extracted from the report")
    impressions: str = Field(default="", description="Overall impression/conclusion from the report")
    flagged_abnormalities: List[str] = Field(default_factory=list, description="Any abnormal results flagged by AI")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When the report was uploaded and analyzed"
    )


# ══════════════════════════════════════════════
#  Phase 1 — Single-Shot Intake Models
# ══════════════════════════════════════════════

class Symptom(BaseModel):
    """A single symptom reported by the patient."""
    name: str = Field(..., description="Name of the symptom (e.g., 'Fever', 'Headache')")
    duration: str = Field(
        default="Not specified",
        description="How long the patient has experienced this symptom"
    )
    details: str = Field(
        default="",
        description="Additional details about the symptom"
    )


class MedicalHistory(BaseModel):
    """Patient's known medical history and allergies."""
    chronic_conditions: List[str] = Field(
        default_factory=list,
        description="List of chronic conditions (e.g., Diabetes, Hypertension)"
    )
    allergies: List[str] = Field(
        default_factory=list,
        description="List of known allergies"
    )


class PatientSummary(BaseModel):
    """
    Structured summary extracted from a patient's spoken statement.
    This is AI-generated and must ALWAYS be verified by a physician.
    """
    age: str = Field(
        default="Not specified",
        description="Patient's age if mentioned"
    )
    symptoms: List[Symptom] = Field(
        default_factory=list,
        description="List of symptoms extracted from the patient's statement"
    )
    medical_history: Optional[MedicalHistory] = Field(
        default=None,
        description="Patient's extracted medical history"
    )
    severity: str = Field(
        default="Not assessed",
        description="AI-estimated severity: Mild, Moderate, or Severe"
    )
    chief_complaint: str = Field(
        default="Not specified",
        description="Primary reason for the visit in a brief phrase"
    )
    additional_notes: str = Field(
        default="",
        description="Any extra context the AI found relevant"
    )
    urgency_level: str = Field(
        default="Not Assessed",
        description="AI-Triage generated urgency level (Emergency, Urgent, Semi-Urgent, Non-Urgent)"
    )


class IntakeResponse(BaseModel):
    """
    Full response from the /api/intake endpoint.
    Contains the raw transcript, structured summary, and a legal disclaimer.
    """
    patient_id: Optional[str] = Field(
        default=None,
        description="Optional patient ID if this intake is linked to a patient profile"
    )
    transcript: str = Field(
        ...,
        description="Raw text transcription of the patient's audio"
    )
    summary: PatientSummary = Field(
        ...,
        description="Structured patient summary extracted by the AI"
    )
    disclaimer: str = Field(
        default=(
            "This is an AI-generated summary. It is NOT a diagnosis. "
            "The treating physician must verify all information with the patient."
        ),
        description="Legal and ethical disclaimer"
    )


class ErrorResponse(BaseModel):
    """Standard error response."""
    detail: str = Field(..., description="Human-readable error message")


# ══════════════════════════════════════════════
#  Phase 2 — Conversation Models
# ══════════════════════════════════════════════

class ConversationState(str, Enum):
    """State of the multi-turn conversation."""
    ASKING = "asking"           # AI is asking follow-up questions
    CONFIRMING = "confirming"   # AI is confirming understanding
    COMPLETE = "complete"       # Conversation finished, summary ready


class ConversationAction(str, Enum):
    """Action type returned by the conversation engine."""
    ASK_FOLLOWUP = "ask_followup"   # AI wants to ask another question
    CONFIRM = "confirm"             # AI wants to confirm understanding
    COMPLETE = "complete"           # AI has all info, final summary ready


class ConversationTurn(BaseModel):
    """A single turn in the conversation."""
    role: str = Field(
        ...,
        description="Who spoke: 'ai' or 'patient'"
    )
    text: str = Field(
        ...,
        description="What was said"
    )
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(),
        description="When this turn occurred"
    )


class ConversationStartResponse(BaseModel):
    """Response when starting a new conversation session."""
    session_id: str = Field(
        ...,
        description="Unique session identifier for this conversation"
    )
    ai_question: str = Field(
        ...,
        description="The AI's opening question"
    )
    audio_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded TTS audio of the AI's question (MP3)"
    )
    turn_number: int = Field(
        default=1,
        description="Current turn number"
    )
    action: str = Field(
        default="ask_followup",
        description="Current action type"
    )


class ConversationResponse(BaseModel):
    """Response for each conversation turn."""
    session_id: str = Field(
        ...,
        description="Session identifier"
    )
    action: ConversationAction = Field(
        ...,
        description="What the AI decided to do"
    )
    ai_text: str = Field(
        default="",
        description="The AI's response text (question, confirmation, or empty)"
    )
    audio_base64: Optional[str] = Field(
        default=None,
        description="Base64-encoded TTS audio (MP3)"
    )
    patient_transcript: str = Field(
        default="",
        description="What the patient said (transcription of their audio)"
    )
    turn_number: int = Field(
        default=1,
        description="Current turn number"
    )
    language: str = Field(
        default="English",
        description="Detected language of the conversation"
    )
    partial_summary: Optional[PatientSummary] = Field(
        default=None,
        description="Partial summary shown during confirmation"
    )
    final_summary: Optional[PatientSummary] = Field(
        default=None,
        description="Final structured summary (only when action=complete)"
    )
    conversation_history: List[ConversationTurn] = Field(
        default_factory=list,
        description="Full conversation history"
    )
    intake_id: Optional[str] = Field(
        default=None,
        description="ID of the created intake record (only when action=complete)"
    )
    disclaimer: str = Field(
        default=(
            "This is an AI-generated summary. It is NOT a diagnosis. "
            "The treating physician must verify all information with the patient."
        ),
        description="Legal and ethical disclaimer"
    )

# ══════════════════════════════════════════════
#  Phase 7 — Queue & Notifications
# ══════════════════════════════════════════════

class QueueStatus(str, Enum):
    WAITING = "waiting"
    IN_CONSULTATION = "in_consultation"
    COMPLETED = "completed"
    SKIPPED = "skipped"

class QueueItem(BaseModel):
    """Represents a patient waiting in the clinic queue."""
    id: str = Field(..., description="Unique queue identifier")
    intake_id: str = Field(..., description="Reference to the intake record ID")
    token_number: str = Field(..., description="Generated token (e.g., G-01, U-02)")
    status: QueueStatus = Field(default=QueueStatus.WAITING)
    urgency_level: str = Field(default="general", description="general or urgent")
    joined_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="When the patient joined the queue"
    )
    expected_time: Optional[str] = Field(None, description="Estimated time of consultation")
    phone_number: Optional[str] = Field(None, description="Patient's phone number for SMS")
