"""
Whisper API integration for audio transcription.

Handles sending audio files to OpenAI's Whisper model and
returning the raw transcription text. Supports multiple audio
formats (webm, wav, mp3, m4a, etc.).
"""

import logging
from pathlib import Path
import os
from openai import OpenAI

logger = logging.getLogger(__name__)


async def transcribe_audio(audio_bytes: bytes, filename: str) -> str:
    """
    Transcribe an audio file using OpenAI's Whisper API.

    Args:
        audio_bytes: Raw bytes of the audio file.
        filename: Original filename (used for format detection).

    Returns:
        The transcribed text as a string.

    Raises:
        ValueError: If the audio file is empty or invalid.
        RuntimeError: If the Whisper API call fails.
    """
    if not audio_bytes:
        raise ValueError("Audio file is empty.")

    # Determine the file extension for Whisper
    suffix = Path(filename).suffix.lower() if filename else ".webm"
    if suffix not in {".webm", ".wav", ".mp3", ".m4a", ".ogg", ".flac", ".mp4", ".mpeg", ".mpga"}:
        logger.warning(f"Unusual audio format '{suffix}', attempting transcription anyway.")

    logger.info(f"Transcribing audio: {filename} ({len(audio_bytes)} bytes, format: {suffix})")

    try:
        client = OpenAI(
            api_key=os.environ.get("GROQ_API_KEY"),
            base_url="https://api.groq.com/openai/v1"
        )

        # Whisper API expects a file-like tuple: (filename, bytes, content_type)
        transcript = client.audio.transcriptions.create(
            model="whisper-large-v3",
            file=(filename or f"audio{suffix}", audio_bytes),
            response_format="text"
        )

        transcribed_text = transcript.strip() if isinstance(transcript, str) else transcript.text.strip()

        if not transcribed_text:
            raise ValueError("Whisper returned an empty transcription.")

        logger.info(f"Transcription complete: {len(transcribed_text)} characters")
        return transcribed_text

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"Whisper API error: {e}")
        raise RuntimeError(f"Transcription failed: {str(e)}") from e
