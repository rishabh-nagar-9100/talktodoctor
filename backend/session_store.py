"""
In-memory session store for conversation state management.

Stores multi-turn conversation sessions keyed by UUID.
Each session holds the full conversation history, detected language,
current state, and partial summary.

NOTE: This is an MVP in-memory store. For production, replace with
Redis or a database-backed store for persistence and scalability.
"""

import asyncio
import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Session expiry time (30 minutes)
SESSION_TTL = timedelta(minutes=30)

# Maximum follow-up questions before forcing confirmation
MAX_FOLLOWUPS = 3


class Session:
    """
    A single conversation session.

    Attributes:
        session_id: Unique identifier.
        messages: List of OpenAI-format messages (role, content).
        turns: List of conversation turns for the frontend.
        state: Current state (asking, confirming, complete).
        language: Detected patient language.
        turn_count: Number of patient turns so far.
        partial_summary: Latest partial summary from the AI.
        final_summary: Final structured summary (when complete).
        created_at: When the session was created.
        updated_at: When the session was last updated.
        tts_audio: Dict of turn_number -> base64 audio.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.messages: list[dict] = []       # OpenAI message format
        self.turns: list[dict] = []          # Frontend-friendly turns
        self.state: str = "asking"
        self.language: str = "English"
        self.turn_count: int = 0
        self.partial_summary: Optional[dict] = None
        self.final_summary: Optional[dict] = None
        self.created_at: datetime = datetime.now(timezone.utc)
        self.updated_at: datetime = datetime.now(timezone.utc)
        self.tts_audio: dict[int, str] = {}  # turn -> base64 audio

    def is_expired(self) -> bool:
        """Check if the session has expired."""
        return datetime.now(timezone.utc) - self.updated_at > SESSION_TTL

    def touch(self):
        """Update the last-accessed timestamp."""
        self.updated_at = datetime.now(timezone.utc)

    def add_ai_turn(self, text: str):
        """Add an AI message to the conversation history."""
        self.messages.append({"role": "assistant", "content": text})
        self.turns.append({
            "role": "ai",
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.touch()

    def add_patient_turn(self, text: str):
        """Add a patient message to the conversation history."""
        self.turn_count += 1
        self.messages.append({"role": "user", "content": text})
        self.turns.append({
            "role": "patient",
            "text": text,
            "timestamp": datetime.now(timezone.utc).isoformat()
        })
        self.touch()

    def should_force_confirm(self) -> bool:
        """Check if we've hit the max follow-up limit."""
        return self.turn_count >= MAX_FOLLOWUPS


class SessionStore:
    """
    Thread-safe in-memory session store.

    Usage:
        store = SessionStore()
        session = await store.create_session()
        session = await store.get_session(session_id)
    """

    def __init__(self):
        self._sessions: dict[str, Session] = {}
        self._lock = asyncio.Lock()

    async def create_session(self) -> Session:
        """Create a new conversation session."""
        async with self._lock:
            session_id = str(uuid.uuid4())
            session = Session(session_id)
            self._sessions[session_id] = session
            logger.info(f"Session created: {session_id}")
            return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve a session by ID.
        Returns None if not found or expired.
        """
        async with self._lock:
            session = self._sessions.get(session_id)
            if session is None:
                return None
            if session.is_expired():
                logger.info(f"Session expired: {session_id}")
                del self._sessions[session_id]
                return None
            session.touch()
            return session

    async def delete_session(self, session_id: str):
        """Delete a session."""
        async with self._lock:
            if session_id in self._sessions:
                del self._sessions[session_id]
                logger.info(f"Session deleted: {session_id}")

    async def cleanup_expired(self):
        """Remove all expired sessions."""
        async with self._lock:
            expired = [
                sid for sid, session in self._sessions.items()
                if session.is_expired()
            ]
            for sid in expired:
                del self._sessions[sid]
            if expired:
                logger.info(f"Cleaned up {len(expired)} expired sessions")

    @property
    def active_count(self) -> int:
        """Number of active sessions."""
        return len(self._sessions)


# ──────────────────────────────────────────────
# Global session store instance
# ──────────────────────────────────────────────
session_store = SessionStore()
