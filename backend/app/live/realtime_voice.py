"""OpenAI Realtime voice bridge for live meetings."""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import time
from contextlib import suppress
from typing import Any, Awaitable, Callable

from app.config import settings

logger = logging.getLogger(__name__)

AudioChunkHandler = Callable[[bytes], Awaitable[None]]
TranscriptHandler = Callable[[str], Awaitable[None]]
StateHandler = Callable[[str, str | None], Awaitable[None]]


class OpenAIRealtimeVoiceBridge:
    def __init__(
        self,
        *,
        on_audio_chunk: AudioChunkHandler,
        on_transcript: TranscriptHandler | None = None,
        on_state: StateHandler | None = None,
        websocket_factory: Callable[..., Awaitable[Any]] | None = None,
    ) -> None:
        self._on_audio_chunk = on_audio_chunk
        self._on_transcript = on_transcript
        self._on_state = on_state
        self._websocket_factory = websocket_factory
        self._ws: Any = None
        self._receive_task: asyncio.Task[Any] | None = None
        self._send_lock = asyncio.Lock()
        self._speak_lock = asyncio.Lock()
        self._ready = asyncio.Event()
        self._pending_speech: asyncio.Future[None] | None = None
        self._response_active = False
        self._last_transcript = ""
        self._last_transcript_at = 0.0

    async def start(self) -> None:
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        websocket_factory = self._websocket_factory
        if websocket_factory is None:
            import websockets

            websocket_factory = websockets.connect

        url = f"wss://api.openai.com/v1/realtime?model={settings.openai_realtime_model}"
        self._ws = await websocket_factory(
            url,
            additional_headers={
                "Authorization": f"Bearer {settings.openai_api_key}",
                "OpenAI-Beta": "realtime=v1",
            },
            max_size=None,
            ping_interval=20,
            ping_timeout=20,
        )
        self._receive_task = asyncio.create_task(self._receive_loop())
        await self._send(
            {
                "type": "session.update",
                "session": {
                    "instructions": (
                        "You are the voice layer for a live software demo assistant. "
                        "Keep speech concise and natural. Do not invent product actions."
                    ),
                    "voice": settings.openai_realtime_voice,
                    "input_audio_format": "pcm16",
                    "output_audio_format": "pcm16",
                    "turn_detection": {
                        "type": "server_vad",
                        "create_response": False,
                        "interrupt_response": True,
                        "silence_duration_ms": settings.openai_realtime_silence_ms,
                        "prefix_padding_ms": 200,
                    },
                    "input_audio_transcription": {
                        "model": settings.openai_realtime_transcription_model,
                    },
                },
            }
        )
        await asyncio.wait_for(self._ready.wait(), timeout=10)

    async def append_audio(self, pcm_bytes: bytes) -> None:
        if not pcm_bytes or self._ws is None:
            return
        await self._send(
            {
                "type": "input_audio_buffer.append",
                "audio": base64.b64encode(pcm_bytes).decode("ascii"),
            }
        )

    async def speak(self, text: str) -> None:
        if not text.strip():
            return
        async with self._speak_lock:
            if self._response_active or (self._pending_speech is not None and not self._pending_speech.done()):
                await self.interrupt()
            loop = asyncio.get_running_loop()
            self._pending_speech = loop.create_future()
            self._response_active = True
            await self._emit_state("speaking", "Agent is responding.")
            await self._send(
                {
                    "type": "response.create",
                    "response": {
                        "modalities": ["audio", "text"],
                        "instructions": (
                            "Speak exactly the following text. "
                            "Do not add, remove, or paraphrase anything.\n\n"
                            f"{text.strip()}"
                        ),
                    },
                }
            )
            try:
                await asyncio.wait_for(self._pending_speech, timeout=30)
            finally:
                self._pending_speech = None

    async def interrupt(self) -> None:
        if self._ws is None:
            return
        if self._response_active or (self._pending_speech is not None and not self._pending_speech.done()):
            with suppress(Exception):
                await self._send({"type": "response.cancel"})
        if self._pending_speech is not None and not self._pending_speech.done():
            self._pending_speech.cancel()
        self._response_active = False
        await self._emit_state("interrupted", "Buyer interrupted the agent.")

    async def stop(self) -> None:
        task = self._receive_task
        if task is not None:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task
            self._receive_task = None
        if self._ws is not None:
            with suppress(Exception):
                await self._ws.close()
            self._ws = None

    async def _receive_loop(self) -> None:
        try:
            async for raw in self._ws:
                event = json.loads(raw)
                await self._handle_event(event)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("OpenAI realtime receive loop failed: %s", exc)
            await self._emit_state("errored", f"Realtime voice failed: {exc}")
            if self._pending_speech is not None and not self._pending_speech.done():
                self._pending_speech.set_exception(RuntimeError(str(exc)))

    async def _handle_event(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("type", ""))
        if event_type in {"session.created", "session.updated"}:
            self._ready.set()
            return

        if event_type in {"input_audio_buffer.speech_started", "input_audio_buffer.speech_stopped"}:
            if event_type.endswith("speech_started"):
                logger.info("OpenAI realtime detected buyer speech start")
                await self._emit_state("listening", "Buyer is speaking.")
            else:
                logger.info("OpenAI realtime detected buyer speech stop")
            return

        if event_type == "conversation.item.input_audio_transcription.completed":
            transcript = _extract_transcript_text(event)
            sanitized, drop_reason = _sanitize_realtime_transcript(
                transcript,
                last_transcript=self._last_transcript,
                last_timestamp=self._last_transcript_at,
                min_chars=settings.voice_min_transcript_chars,
            )
            if sanitized and self._on_transcript is not None:
                logger.info("OpenAI realtime transcript accepted: %s", sanitized)
                self._last_transcript = sanitized
                self._last_transcript_at = time.monotonic()
                await self._emit_state("thinking", "Agent is processing your question.")
                await self._on_transcript(sanitized)
            else:
                logger.info(
                    "OpenAI realtime transcript dropped: raw=%r reason=%s",
                    transcript,
                    drop_reason or "no_handler",
                )
            return

        if event_type == "response.audio.delta":
            delta = event.get("delta")
            if delta:
                await self._on_audio_chunk(base64.b64decode(delta))
            return

        if event_type in {"response.done", "response.completed"}:
            self._response_active = False
            if self._pending_speech is not None and not self._pending_speech.done():
                self._pending_speech.set_result(None)
            return

        if event_type == "error":
            detail = _extract_error_message(event)
            if _is_benign_realtime_error(detail):
                logger.debug("Ignoring benign OpenAI realtime event error: %s", detail)
                return
            self._response_active = False
            logger.warning("OpenAI realtime event error: %s", detail)
            await self._emit_state("errored", detail)
            if self._pending_speech is not None and not self._pending_speech.done():
                self._pending_speech.set_exception(RuntimeError(detail))

    async def _send(self, payload: dict[str, Any]) -> None:
        if self._ws is None:
            raise RuntimeError("Realtime voice session is not connected")
        async with self._send_lock:
            await self._ws.send(json.dumps(payload))

    async def _emit_state(self, state: str, detail: str | None) -> None:
        if self._on_state is not None:
            await self._on_state(state, detail)


def _extract_error_message(event: dict[str, Any]) -> str:
    error = event.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or error.get("code") or "OpenAI realtime error")
    return str(error or "OpenAI realtime error")


def _extract_transcript_text(event: dict[str, Any]) -> str:
    transcript = event.get("transcript")
    if isinstance(transcript, str):
        return transcript
    item = event.get("item")
    if isinstance(item, dict):
        for content in item.get("content", []):
            if isinstance(content, dict) and isinstance(content.get("transcript"), str):
                return content["transcript"]
    return ""


def _sanitize_realtime_transcript(
    transcript: str,
    *,
    last_transcript: str,
    last_timestamp: float,
    min_chars: int,
) -> tuple[str, str | None]:
    cleaned = " ".join(transcript.split()).strip()
    if len(cleaned) < min_chars:
        return "", "too_short"
    lowered = cleaned.lower()
    if lowered == last_transcript.lower() and (time.monotonic() - last_timestamp) < 1.5:
        return "", "duplicate"
    if _looks_repetitive(lowered):
        return "", "repetitive"
    return cleaned, None


def _looks_repetitive(text: str) -> bool:
    words = [token for token in text.split() if token]
    if not words:
        return True
    if len(words) >= 4 and len(set(words)) == 1:
        return True
    if len(words) >= 6:
        most_common = max(words.count(word) for word in set(words))
        if most_common / len(words) >= 0.6:
            return True
    if len(text) >= 12 and len(set(text.replace(" ", ""))) <= 3:
        return True
    filler = {"uh", "um", "yeah", "okay", "ok", "sorry", "so"}
    if len(words) >= 5 and set(words).issubset(filler):
        return True
    return False


def _is_benign_realtime_error(detail: str) -> bool:
    lowered = detail.lower()
    return "no active response found" in lowered or "buffer too small" in lowered
