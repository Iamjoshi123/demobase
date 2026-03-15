"""Voice session management using LiveKit Agents.

When ENABLE_VOICE=true, provides real-time voice conversation.
Otherwise, serves as a stub that returns text-only mode.
"""

import logging
import asyncio
from typing import Optional
from app.config import settings

logger = logging.getLogger(__name__)
_whisper_model = None
_whisper_model_lock = asyncio.Lock()


class VoiceSession:
    """Manages a single voice session with a buyer."""

    def __init__(self, session_id: str, workspace_id: str):
        self.session_id = session_id
        self.workspace_id = workspace_id
        self.is_active = False
        self._room_name: Optional[str] = None
        self._token: Optional[str] = None

    async def start(self) -> dict:
        """Start a voice session. Returns connection info for the frontend."""
        if not settings.enable_voice:
            logger.info("Voice disabled, returning text-only mode")
            return {
                "mode": "text",
                "message": "Voice is not configured. Using text chat mode.",
            }

        try:
            return await self._create_livekit_room()
        except Exception as e:
            logger.error(f"Failed to start voice session: {e}")
            return {
                "mode": "text",
                "message": f"Voice unavailable: {e}. Falling back to text chat.",
            }

    async def _create_livekit_room(self) -> dict:
        """Create a LiveKit room and generate participant token."""
        try:
            from livekit import api as livekit_api

            self._room_name = f"demo-{self.session_id}"

            # Generate token for buyer
            token = livekit_api.AccessToken(
                settings.livekit_api_key,
                settings.livekit_api_secret,
            )
            token.with_identity(f"buyer-{self.session_id}")
            token.with_name("Demo Buyer")
            token.with_grants(livekit_api.VideoGrants(
                room_join=True,
                room=self._room_name,
            ))

            self._token = token.to_jwt()
            self.is_active = True

            return {
                "mode": "voice",
                "livekit_url": settings.livekit_url,
                "token": self._token,
                "room_name": self._room_name,
            }
        except ImportError:
            logger.warning("LiveKit SDK not installed")
            return {
                "mode": "text",
                "message": "LiveKit SDK not installed. Using text chat.",
            }

    async def stop(self) -> None:
        """Stop the voice session."""
        self.is_active = False
        self._token = None
        logger.info(f"Voice session stopped for {self.session_id}")


async def transcribe_audio(audio_bytes: bytes) -> str:
    """Transcribe audio bytes to text using faster-whisper.

    Falls back to returning empty string if faster-whisper is unavailable.
    """
    try:
        model = await _get_whisper_model()
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            f.write(audio_bytes)
            tmp_path = f.name

        try:
            segments, _ = model.transcribe(
                tmp_path,
                language=settings.voice_language,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                vad_filter=False,
                condition_on_previous_text=False,
            )
            text = " ".join(segment.text for segment in segments).strip()
            text = _sanitize_transcript(text)
            if len(text) < settings.voice_min_transcript_chars:
                return ""
            return text
        finally:
            os.unlink(tmp_path)
    except ImportError:
        logger.warning("faster-whisper not installed, cannot transcribe")
        return ""
    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return ""


async def _get_whisper_model():
    global _whisper_model
    if _whisper_model is not None:
        return _whisper_model

    async with _whisper_model_lock:
        if _whisper_model is not None:
            return _whisper_model

        from faster_whisper import WhisperModel

        _whisper_model = WhisperModel(settings.voice_whisper_model, device="cpu", compute_type="int8")
        return _whisper_model


def _sanitize_transcript(text: str) -> str:
    cleaned = " ".join(text.split()).strip()
    if not cleaned:
        return ""

    sentence = cleaned.rstrip(".!? ").strip()
    if not sentence:
        return ""

    repeated = f"{sentence}. {sentence}".lower()
    if repeated in cleaned.lower() or _has_repeated_phrase(sentence):
        return ""

    return cleaned


def _has_repeated_phrase(sentence: str) -> bool:
    tokens = sentence.lower().split()
    if len(tokens) < 4:
        return False

    for size in range(4, min(10, len(tokens) // 2 + 1)):
        chunk = " ".join(tokens[:size])
        repeated = " ".join([chunk] * 3)
        if repeated in " ".join(tokens):
            return True
    return False
