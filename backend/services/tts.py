"""
Text-to-Speech service using gTTS (Google Text-to-Speech).

Converts AI text responses into spoken audio so the patient
can hear the follow-up questions through the kiosk.

Returns base64-encoded MP3 audio for easy frontend consumption.
"""

import base64
import io
import logging
from gtts import gTTS

logger = logging.getLogger(__name__)

# Kept for compatibility with existing imports
DEFAULT_VOICE = "gTTS"
DEFAULT_MODEL = "gTTS"


async def generate_speech(
    text: str,
    voice: str = DEFAULT_VOICE,
    model: str = DEFAULT_MODEL,
) -> str:
    """
    Generate speech audio from text using gTTS API.

    Args:
        text: The text to convert to speech.
        voice: Ignored (kept for backward compatibility).
        model: Ignored (kept for backward compatibility).

    Returns:
        Base64-encoded MP3 audio string.

    Raises:
        ValueError: If text is empty.
        RuntimeError: If the TTS API call fails.
    """
    if not text or not text.strip():
        raise ValueError("Cannot generate speech from empty text.")

    logger.info(f"Generating TTS using gTTS: '{text[:60]}...'")

    try:
        tts = gTTS(text=text, lang='en')
        fp = io.BytesIO()
        tts.write_to_fp(fp)
        fp.seek(0)
        audio_bytes = fp.read()

        if not audio_bytes:
            raise RuntimeError("gTTS returned empty audio.")

        # Encode as base64 for easy transport to frontend
        audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")

        logger.info(f"TTS generated: {len(audio_bytes)} bytes ({len(audio_base64)} base64 chars)")
        return audio_base64

    except ValueError:
        raise
    except Exception as e:
        logger.error(f"TTS error: {e}")
        raise RuntimeError(f"Speech generation failed: {str(e)}") from e
