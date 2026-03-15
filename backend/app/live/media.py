"""Media publishing adapters for live demo sessions."""

from __future__ import annotations

import asyncio
import io
import logging
import math
import re
import tempfile
import time
import wave
from abc import ABC, abstractmethod
from contextlib import suppress
from pathlib import Path
from typing import Any, Awaitable, Callable

from app.config import settings
from app.live.room import LiveKitParticipantContract
from app.live.realtime_voice import OpenAIRealtimeVoiceBridge

logger = logging.getLogger(__name__)

TranscriptHandler = Callable[[str], Awaitable[None]]
SpeechActivityHandler = Callable[[], Awaitable[None]]
StartupStateHandler = Callable[[str, str | None], Awaitable[None]]
AGENT_AUDIO_SAMPLE_RATE = 24000
AGENT_AUDIO_CHANNELS = 1
PCM_SAMPLE_WIDTH = 2
BUYER_AUDIO_SAMPLE_RATE = 16000
BUYER_AUDIO_CHANNELS = 1
TRANSCRIPT_CHUNK_SECONDS = 0.8
BUYER_AUDIO_RMS_GATE = 140
BUYER_BARGE_IN_COOLDOWN_SECONDS = 0.35
BUYER_SILENCE_FLUSH_SECONDS = 0.28
BUYER_MIN_VOICE_SECONDS = 0.22
AGENT_TTS_SEGMENT_MAX_CHARS = 220
VAD_FRAME_MS = 30


class MediaPublisher(ABC):
    @abstractmethod
    async def start(
        self,
        driver: Any,
        agent_contract: LiveKitParticipantContract,
        browser_contract: LiveKitParticipantContract | None = None,
        on_transcript: TranscriptHandler | None = None,
        on_speech_activity: SpeechActivityHandler | None = None,
        on_startup_state: StartupStateHandler | None = None,
    ) -> None:
        raise NotImplementedError

    @abstractmethod
    async def speak(self, text: str) -> None:
        raise NotImplementedError

    async def interrupt_speech(self) -> None:
        return None

    @abstractmethod
    async def stop(self) -> None:
        raise NotImplementedError


class NullMediaPublisher(MediaPublisher):
    async def start(
        self,
        driver: Any,
        agent_contract: LiveKitParticipantContract,
        browser_contract: LiveKitParticipantContract | None = None,
        on_transcript: TranscriptHandler | None = None,
        on_speech_activity: SpeechActivityHandler | None = None,
        on_startup_state: StartupStateHandler | None = None,
    ) -> None:
        return None

    async def speak(self, text: str) -> None:
        return None

    async def stop(self) -> None:
        return None


class LiveKitBrowserPublisher(MediaPublisher):
    """Publish the running Playwright page into a LiveKit room."""

    def __init__(self) -> None:
        self._rtc: Any = None
        self._room: Any = None
        self._audio_output: Any = None
        self._video_source: Any = None
        self._video_track: Any = None
        self._video_publication: Any = None
        self._driver: Any = None
        self._on_transcript: TranscriptHandler | None = None
        self._on_speech_activity: SpeechActivityHandler | None = None
        self._on_startup_state: StartupStateHandler | None = None
        self._audio_tasks: set[asyncio.Task[Any]] = set()
        self._transcription_tasks: set[asyncio.Task[Any]] = set()
        self._transcription_lock = asyncio.Lock()
        self._speak_task: asyncio.Task[Any] | None = None
        self._last_barge_in_at = 0.0
        self._published_browser_frames = 0
        self._buyer_audio_ready_reported = False

    async def start(
        self,
        driver: Any,
        agent_contract: LiveKitParticipantContract,
        browser_contract: LiveKitParticipantContract | None = None,
        on_transcript: TranscriptHandler | None = None,
        on_speech_activity: SpeechActivityHandler | None = None,
        on_startup_state: StartupStateHandler | None = None,
    ) -> None:
        from PIL import Image
        from livekit import rtc
        from livekit.agents.voice.room_io._output import _ParticipantAudioOutput
        from livekit.rtc._proto import track_pb2 as proto_track

        self._rtc = rtc
        self._image_module = Image
        self._driver = driver
        self._on_transcript = on_transcript
        self._on_speech_activity = on_speech_activity
        self._on_startup_state = on_startup_state
        self._buyer_audio_ready_reported = False

        self._room = rtc.Room()
        await self._room.connect(agent_contract.livekit_url, agent_contract.token)
        await self._emit_startup_state(
            "room_connected",
            f"Connected voice participant {agent_contract.participant_identity}.",
        )

        audio_options = rtc.TrackPublishOptions()
        audio_options.source = proto_track.SOURCE_MICROPHONE
        self._audio_output = _ParticipantAudioOutput(
            self._room,
            sample_rate=AGENT_AUDIO_SAMPLE_RATE,
            num_channels=AGENT_AUDIO_CHANNELS,
            track_publish_options=audio_options,
            track_name="agent-audio",
        )
        await self._audio_output.start()
        await self._emit_startup_state(
            "agent_audio_ready",
            f"Agent audio track is publishing from {agent_contract.participant_identity}.",
        )

        self._video_source = rtc.VideoSource(width=1280, height=720)
        self._video_track = rtc.LocalVideoTrack.create_video_track("browser-video", self._video_source)
        video_options = rtc.TrackPublishOptions()
        video_options.source = proto_track.SOURCE_SCREENSHARE
        video_options.simulcast = False
        video_options.stream = "browser-stage"
        video_options.video_encoding.max_framerate = 8.0
        video_options.video_encoding.max_bitrate = 4_000_000
        logger.info(
            "Publishing browser-video track with source=%s simulcast=%s max_framerate=%s max_bitrate=%s",
            video_options.source,
            video_options.simulcast,
            video_options.video_encoding.max_framerate,
            video_options.video_encoding.max_bitrate,
        )
        self._video_publication = await self._room.local_participant.publish_track(self._video_track, video_options)
        logger.info(
            "browser-video publication ready sid=%s name=%s participant=%s",
            getattr(self._video_publication, "sid", "unknown"),
            getattr(self._video_track, "name", "browser-video"),
            agent_contract.participant_identity,
        )
        await self._emit_startup_state(
            "browser_publisher_ready",
            f"Browser video track is publishing from {agent_contract.participant_identity}.",
        )

        if settings.enable_voice:
            self._register_audio_handler()

        await driver.start_frame_stream(self._publish_browser_frame)

    async def speak(self, text: str) -> None:
        if not text or self._audio_output is None:
            return
        self._interrupt_speech_now()
        task = asyncio.create_task(self._speak_impl(text))
        self._speak_task = task
        try:
            await task
        except asyncio.CancelledError:
            logger.info("Agent speech interrupted for live session")
        finally:
            if self._speak_task is task:
                self._speak_task = None

    async def interrupt_speech(self) -> None:
        self._interrupt_speech_now()
        task = self._speak_task
        if task is None:
            return
        with suppress(asyncio.CancelledError):
            await task

    async def stop(self) -> None:
        await self.interrupt_speech()
        for task in list(self._audio_tasks):
            task.cancel()
        self._audio_tasks.clear()
        for task in list(self._transcription_tasks):
            task.cancel()
        self._transcription_tasks.clear()

        if self._driver is not None:
            try:
                await self._driver.stop_frame_stream()
            except Exception as exc:  # pragma: no cover - best-effort cleanup
                logger.debug("Failed stopping browser frame stream: %s", exc)

        if self._video_publication is not None and self._room is not None:
            with suppress(Exception):
                await self._room.local_participant.unpublish_track(self._video_publication.sid)
            self._video_publication = None
        if self._video_source is not None:
            try:
                await self._video_source.aclose()
            except Exception as exc:  # pragma: no cover - best-effort cleanup
                logger.debug("Failed closing browser video source: %s", exc)
            self._video_source = None
        self._video_track = None

        if self._room is not None:
            try:
                await self._room.disconnect()
            except Exception as exc:  # pragma: no cover - best-effort cleanup
                logger.debug("Failed disconnecting LiveKit room: %s", exc)
            self._room = None
        self._audio_output = None

    async def _publish_track(self, track: Any, source: Any) -> None:
        options = None
        if source is not None and hasattr(self._rtc, "TrackPublishOptions"):
            try:
                options = self._rtc.TrackPublishOptions(source=source)
            except TypeError:
                options = None

        if options is not None:
            await self._room.local_participant.publish_track(track, options)
        else:
            await self._room.local_participant.publish_track(track)

    async def _publish_browser_frame(self, payload: bytes, width: int, height: int) -> None:
        if self._video_source is None:
            return
        frame, average = _image_payload_to_video_frame(self._rtc, self._image_module, payload)
        self._published_browser_frames += 1
        if self._published_browser_frames <= 3 or self._published_browser_frames % 20 == 0:
            logger.info(
                "Publishing browser frame #%s: source=%sx%s frame=%sx%s avg_brightness=%.2f bytes=%s",
                self._published_browser_frames,
                width,
                height,
                getattr(frame, "width", width),
                getattr(frame, "height", height),
                average,
                len(payload),
            )
        timestamp_us = time.time_ns() // 1000
        self._video_source.capture_frame(frame, timestamp_us=timestamp_us)

    def _register_audio_handler(self) -> None:
        if self._on_transcript is None:
            return

        def on_track_subscribed(track: Any, publication: Any, participant: Any) -> None:
            if not self._should_consume_audio_track(publication, participant):
                return
            kind = getattr(track, "kind", None)
            audio_kind = getattr(self._rtc.TrackKind, "KIND_AUDIO", None)
            if audio_kind is not None and kind != audio_kind:
                return
            logger.info(
                "Subscribed to buyer audio track '%s' from participant %s",
                getattr(publication, "name", "unknown"),
                getattr(participant, "identity", "unknown"),
            )
            self._mark_buyer_audio_ready(getattr(participant, "identity", "unknown"))
            task = asyncio.create_task(self._consume_audio_track(track))
            self._audio_tasks.add(task)
            task.add_done_callback(self._audio_tasks.discard)

        self._room.on("track_subscribed", on_track_subscribed)
        self._consume_existing_buyer_audio_tracks(on_track_subscribed)

    def _consume_existing_buyer_audio_tracks(self, on_track_subscribed: Callable[[Any, Any, Any], None]) -> None:
        if self._room is None:
            return
        for participant in getattr(self._room, "remote_participants", {}).values():
            for publication in getattr(participant, "track_publications", {}).values():
                if not self._should_consume_audio_track(publication, participant):
                    continue
                if hasattr(publication, "set_subscribed"):
                    try:
                        publication.set_subscribed(True)
                    except Exception as exc:
                        logger.debug(
                            "Failed forcing subscription for buyer audio track '%s': %s",
                            getattr(publication, "name", "unknown"),
                            exc,
                        )
                track = getattr(publication, "track", None)
                if track is not None:
                    logger.info(
                        "Found existing buyer audio track '%s' from participant %s during media attach",
                        getattr(publication, "name", "unknown"),
                        getattr(participant, "identity", "unknown"),
                    )
                    on_track_subscribed(track, publication, participant)

    def _should_consume_audio_track(self, publication: Any, participant: Any) -> bool:
        identity = str(getattr(participant, "identity", "") or "")
        track_name = str(getattr(publication, "name", "") or "")
        if track_name == "agent-audio":
            return False
        if identity and not identity.startswith("buyer-"):
            return False
        return True

    def _mark_buyer_audio_ready(self, participant_identity: str) -> None:
        if self._buyer_audio_ready_reported:
            return
        self._buyer_audio_ready_reported = True
        task = asyncio.create_task(
            self._emit_startup_state(
                "buyer_audio_ready",
                f"Buyer audio is subscribed from {participant_identity}.",
            )
        )
        self._transcription_tasks.add(task)
        task.add_done_callback(self._transcription_tasks.discard)

    async def _consume_audio_track(self, track: Any) -> None:
        try:
            stream = self._rtc.AudioStream(track, sample_rate=BUYER_AUDIO_SAMPLE_RATE, num_channels=BUYER_AUDIO_CHANNELS)
        except TypeError:
            stream = self._rtc.AudioStream.from_track(
                track=track,
                sample_rate=BUYER_AUDIO_SAMPLE_RATE,
                num_channels=BUYER_AUDIO_CHANNELS,
            )

        frames: list[bytes] = []
        sample_rate = BUYER_AUDIO_SAMPLE_RATE
        chunk_frames = 0
        speech_frames = 0
        silence_frames = 0
        silence_flush_frames = int(sample_rate * BUYER_SILENCE_FLUSH_SECONDS)
        min_voice_frames = int(sample_rate * BUYER_MIN_VOICE_SECONDS)

        async for event in stream:
            frame = getattr(event, "frame", event)
            data = getattr(frame, "data", None)
            if not data:
                continue
            pcm_chunk = bytes(data)
            samples_per_channel = int(getattr(frame, "samples_per_channel", 0) or 0)
            if not samples_per_channel:
                continue
            is_speech = _chunk_contains_speech(pcm_chunk, sample_rate)

            if is_speech:
                self._maybe_interrupt_for_barge_in(pcm_chunk)
                frames.append(pcm_chunk)
                chunk_frames += samples_per_channel
                speech_frames += samples_per_channel
                silence_frames = 0
            elif speech_frames > 0:
                frames.append(pcm_chunk)
                chunk_frames += samples_per_channel
                silence_frames += samples_per_channel
            else:
                continue

            if speech_frames >= min_voice_frames and silence_frames >= silence_flush_frames:
                self._queue_transcription(b"".join(frames), sample_rate)
                frames = []
                chunk_frames = 0
                speech_frames = 0
                silence_frames = 0
                continue

            if chunk_frames >= int(sample_rate * TRANSCRIPT_CHUNK_SECONDS):
                self._queue_transcription(b"".join(frames), sample_rate)
                frames = []
                chunk_frames = 0
                speech_frames = 0
                silence_frames = 0

        if frames and speech_frames > 0:
            self._queue_transcription(b"".join(frames), sample_rate)

    def _queue_transcription(self, pcm_bytes: bytes, sample_rate: int) -> None:
        if self._on_transcript is None or not pcm_bytes:
            return
        if _pcm_rms(pcm_bytes) < BUYER_AUDIO_RMS_GATE:
            return
        if self._transcription_lock.locked():
            return
        task = asyncio.create_task(self._transcribe_and_forward(pcm_bytes, sample_rate))
        self._transcription_tasks.add(task)
        task.add_done_callback(self._transcription_tasks.discard)

    async def _transcribe_and_forward(self, pcm_bytes: bytes, sample_rate: int) -> None:
        async with self._transcription_lock:
            try:
                transcript = await self._transcribe_pcm(pcm_bytes, sample_rate)
                if transcript:
                    logger.info("Forwarding voice transcript: %s", transcript)
                    await self._on_transcript(transcript)
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning("Voice transcription forwarding failed: %s", exc)

    async def _transcribe_pcm(self, pcm_bytes: bytes, sample_rate: int) -> str:
        if not pcm_bytes:
            return ""
        from app.voice.session import transcribe_audio

        wav_bytes = _pcm_to_wav_bytes(pcm_bytes, sample_rate)
        return await transcribe_audio(wav_bytes)

    async def _speak_impl(self, text: str) -> None:
        for segment in _split_agent_speech(text):
            audio_bytes = await asyncio.to_thread(_synthesize_speech_audio, segment)
            await self._publish_audio_bytes(audio_bytes)

    def _interrupt_speech_now(self) -> None:
        task = self._speak_task
        if task is not None and not task.done():
            task.cancel()
        self._clear_agent_audio_queue()

    def _maybe_interrupt_for_barge_in(self, pcm_bytes: bytes) -> None:
        if _pcm_rms(pcm_bytes) < BUYER_AUDIO_RMS_GATE:
            return
        now = time.monotonic()
        if now - self._last_barge_in_at < BUYER_BARGE_IN_COOLDOWN_SECONDS:
            return
        self._last_barge_in_at = now
        self._interrupt_speech_now()
        if self._on_speech_activity is not None:
            task = asyncio.create_task(self._on_speech_activity())
            self._transcription_tasks.add(task)
            task.add_done_callback(self._transcription_tasks.discard)

    async def _publish_audio_bytes(self, audio_bytes: bytes) -> None:
        if self._audio_output is None:
            return
        raw = _trim_silence(
            _normalize_audio_bytes(
                audio_bytes,
                sample_rate=AGENT_AUDIO_SAMPLE_RATE,
                num_channels=AGENT_AUDIO_CHANNELS,
            )
        )

        bytes_per_frame = AGENT_AUDIO_CHANNELS * PCM_SAMPLE_WIDTH
        samples_per_chunk = max(AGENT_AUDIO_SAMPLE_RATE // 50, 1)
        chunk_size = samples_per_chunk * bytes_per_frame

        for offset in range(0, len(raw), chunk_size):
            chunk = raw[offset: offset + chunk_size]
            samples_in_chunk = max(len(chunk) // bytes_per_frame, 1)
            frame = self._rtc.AudioFrame(
                data=chunk,
                sample_rate=AGENT_AUDIO_SAMPLE_RATE,
                num_channels=AGENT_AUDIO_CHANNELS,
                samples_per_channel=samples_in_chunk,
            )
            await self._audio_output.capture_frame(frame)
            await asyncio.sleep(samples_in_chunk / AGENT_AUDIO_SAMPLE_RATE)
        self._audio_output.flush()

    def _clear_agent_audio_queue(self) -> None:
        if self._audio_output is not None:
            try:
                self._audio_output.clear_buffer()
                return
            except Exception as exc:
                logger.debug("Failed clearing agent audio buffer: %s", exc)
        legacy_audio_source = getattr(self, "_audio_source", None)
        if legacy_audio_source is not None:
            try:
                legacy_audio_source.clear_queue()
            except Exception as exc:
                logger.debug("Failed clearing legacy audio queue during barge-in: %s", exc)

    async def _emit_startup_state(self, state: str, detail: str | None) -> None:
        if self._on_startup_state is not None:
            await self._on_startup_state(state, detail)


class OpenAIRealtimeMediaPublisher(LiveKitBrowserPublisher):
    """LiveKit browser publisher with OpenAI Realtime-powered voice."""

    def __init__(self) -> None:
        super().__init__()
        self._voice_bridge: OpenAIRealtimeVoiceBridge | None = None
        self._audio_remainder = bytearray()

    async def start(
        self,
        driver: Any,
        agent_contract: LiveKitParticipantContract,
        browser_contract: LiveKitParticipantContract | None = None,
        on_transcript: TranscriptHandler | None = None,
        on_speech_activity: SpeechActivityHandler | None = None,
        on_startup_state: StartupStateHandler | None = None,
    ) -> None:
        await super().start(
            driver,
            agent_contract,
            browser_contract=browser_contract,
            on_transcript=on_transcript,
            on_speech_activity=on_speech_activity,
            on_startup_state=on_startup_state,
        )
        if self._audio_output is None:
            raise RuntimeError("Agent audio track is not available for realtime voice")
        self._voice_bridge = OpenAIRealtimeVoiceBridge(
            on_audio_chunk=self._publish_realtime_pcm,
            on_transcript=on_transcript,
            on_state=self._handle_realtime_state,
        )
        await self._voice_bridge.start()

    async def speak(self, text: str) -> None:
        if not text or self._voice_bridge is None:
            return
        self._interrupt_speech_now()
        self._speak_task = asyncio.create_task(self._voice_bridge.speak(text))
        try:
            await self._speak_task
            if self._audio_output is not None:
                self._audio_output.flush()
        except asyncio.CancelledError:
            logger.info("Agent speech interrupted for live session")
        finally:
            self._speak_task = None

    async def interrupt_speech(self) -> None:
        self._interrupt_speech_now()
        if self._voice_bridge is not None:
            await self._voice_bridge.interrupt()
        await super().interrupt_speech()

    async def stop(self) -> None:
        if self._voice_bridge is not None:
            await self._voice_bridge.stop()
            self._voice_bridge = None
        await super().stop()

    async def _consume_audio_track(self, track: Any) -> None:
        if self._voice_bridge is None:
            await super()._consume_audio_track(track)
            return
        try:
            stream = self._rtc.AudioStream(track, sample_rate=BUYER_AUDIO_SAMPLE_RATE, num_channels=BUYER_AUDIO_CHANNELS)
        except TypeError:
            stream = self._rtc.AudioStream.from_track(
                track=track,
                sample_rate=BUYER_AUDIO_SAMPLE_RATE,
                num_channels=BUYER_AUDIO_CHANNELS,
            )

        async for event in stream:
            frame = getattr(event, "frame", event)
            data = getattr(frame, "data", None)
            if not data:
                continue
            pcm_chunk = bytes(data)
            try:
                await self._voice_bridge.append_audio(pcm_chunk)
            except Exception as exc:
                logger.warning("Failed forwarding buyer audio to OpenAI realtime: %s", exc)
                break

    async def _handle_realtime_state(self, state: str, detail: str | None) -> None:
        if state == "listening" and self._on_speech_activity is not None:
            task = asyncio.create_task(self._on_speech_activity())
            self._transcription_tasks.add(task)
            task.add_done_callback(self._transcription_tasks.discard)

    async def _publish_realtime_pcm(self, pcm_bytes: bytes) -> None:
        if self._audio_output is None or not pcm_bytes:
            return
        self._audio_remainder.extend(pcm_bytes)
        bytes_per_frame = AGENT_AUDIO_CHANNELS * PCM_SAMPLE_WIDTH
        aligned = len(self._audio_remainder) - (len(self._audio_remainder) % bytes_per_frame)
        if aligned <= 0:
            return
        chunk = bytes(self._audio_remainder[:aligned])
        del self._audio_remainder[:aligned]
        samples = max(len(chunk) // bytes_per_frame, 1)
        frame = self._rtc.AudioFrame(
            data=chunk,
            sample_rate=AGENT_AUDIO_SAMPLE_RATE,
            num_channels=AGENT_AUDIO_CHANNELS,
            samples_per_channel=samples,
        )
        await self._audio_output.capture_frame(frame)

    def _interrupt_speech_now(self) -> None:
        self._audio_remainder.clear()
        super()._interrupt_speech_now()


def create_media_publisher() -> MediaPublisher:
    if settings.app_env == "test":
        return NullMediaPublisher()
    if settings.enable_voice and settings.voice_provider.lower() == "openai_realtime" and settings.has_openai:
        logger.info("Using OpenAI Realtime media publisher")
        return OpenAIRealtimeMediaPublisher()
    if settings.enable_voice and settings.voice_provider.lower() == "openai_realtime" and not settings.has_openai:
        logger.warning("VOICE_PROVIDER=openai_realtime but OPENAI_API_KEY is missing; falling back to local voice stack")
    return LiveKitBrowserPublisher()


def _synthesize_speech_audio(text: str) -> bytes:
    provider = (settings.voice_tts_provider or "auto").lower()
    if provider in {"auto", "edge"}:
        try:
            return _synthesize_speech_with_edge_tts(text, settings.voice_tts_voice)
        except ImportError:
            logger.debug("edge-tts not installed, falling back to pyttsx3")
        except Exception as exc:
            logger.warning("edge-tts synthesis failed, falling back to pyttsx3: %s", exc)
            if provider == "edge":
                raise
    return _synthesize_speech_with_pyttsx3(text)


def _synthesize_speech_with_edge_tts(text: str, voice: str) -> bytes:
    import edge_tts

    async def _run() -> bytes:
        chunks: list[bytes] = []
        communicate = edge_tts.Communicate(text, voice=voice)
        async for chunk in communicate.stream():
            if chunk.get("type") == "audio":
                data = chunk.get("data")
                if data:
                    chunks.append(data)
        return b"".join(chunks)

    return asyncio.run(_run())


def _synthesize_speech_with_pyttsx3(text: str) -> bytes:
    import pyttsx3
    import pythoncom

    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        temp_path = Path(tmp.name)

    try:
        pythoncom.CoInitialize()
        engine = pyttsx3.init()
        engine.save_to_file(text, str(temp_path))
        engine.runAndWait()
        return temp_path.read_bytes()
    finally:
        try:
            pythoncom.CoUninitialize()
        except Exception:
            pass
        temp_path.unlink(missing_ok=True)


def _pcm_to_wav_bytes(pcm_bytes: bytes, sample_rate: int) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav_file:
        wav_file.setnchannels(AGENT_AUDIO_CHANNELS)
        wav_file.setsampwidth(PCM_SAMPLE_WIDTH)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(pcm_bytes)
    return buffer.getvalue()


def _image_payload_to_video_frame(rtc_module: Any, image_module: Any, payload: bytes) -> tuple[Any, float]:
    from livekit.rtc._proto import video_frame_pb2 as proto_video

    image = image_module.open(io.BytesIO(payload)).convert("RGB")
    pixel_bytes = image.tobytes()
    average = sum(pixel_bytes) / len(pixel_bytes) if pixel_bytes else 0.0
    frame = rtc_module.VideoFrame(
        image.width,
        image.height,
        proto_video.VideoBufferType.RGB24,
        pixel_bytes,
    )
    return frame.convert(proto_video.VideoBufferType.I420), average


def _normalize_audio_bytes(audio_bytes: bytes, *, sample_rate: int, num_channels: int) -> bytes:
    import av

    output = bytearray()
    with av.open(io.BytesIO(audio_bytes), mode="r") as container:
        stream = container.streams.audio[0]
        resampler = av.audio.resampler.AudioResampler(
            format="s16",
            layout="mono" if num_channels == 1 else "stereo",
            rate=sample_rate,
        )
        for packet in container.demux(stream):
            for frame in packet.decode():
                resampled_frames = resampler.resample(frame)
                if not isinstance(resampled_frames, list):
                    resampled_frames = [resampled_frames]
                for resampled in resampled_frames:
                    if resampled is None:
                        continue
                    output.extend(bytes(resampled.planes[0]))

        flushed_frames = resampler.resample(None)
        if flushed_frames:
            if not isinstance(flushed_frames, list):
                flushed_frames = [flushed_frames]
            for frame in flushed_frames:
                if frame is None:
                    continue
                output.extend(bytes(frame.planes[0]))

    return bytes(output)


def _trim_silence(raw_pcm: bytes, threshold: int = 64) -> bytes:
    if not raw_pcm:
        return raw_pcm

    frame_size = PCM_SAMPLE_WIDTH * AGENT_AUDIO_CHANNELS
    start = 0
    end = len(raw_pcm)

    while start + frame_size <= end:
        if _pcm_rms(raw_pcm[start:start + frame_size]) > threshold:
            break
        start += frame_size

    while end - frame_size >= start:
        if _pcm_rms(raw_pcm[end - frame_size:end]) > threshold:
            break
        end -= frame_size

    trimmed = raw_pcm[start:end]
    return trimmed if trimmed else raw_pcm


def _pcm_rms(frame_bytes: bytes) -> float:
    if not frame_bytes:
        return 0.0
    samples = [
        int.from_bytes(frame_bytes[index:index + PCM_SAMPLE_WIDTH], "little", signed=True)
        for index in range(0, len(frame_bytes), PCM_SAMPLE_WIDTH)
    ]
    if not samples:
        return 0.0
    mean_square = sum(sample * sample for sample in samples) / len(samples)
    return math.sqrt(mean_square)


def _chunk_contains_speech(pcm_bytes: bytes, sample_rate: int) -> bool:
    if not pcm_bytes:
        return False
    try:
        return _vad_contains_speech(pcm_bytes, sample_rate)
    except ImportError:
        return _pcm_rms(pcm_bytes) >= BUYER_AUDIO_RMS_GATE
    except Exception as exc:
        logger.debug("WebRTC VAD failed, falling back to RMS gate: %s", exc)
        return _pcm_rms(pcm_bytes) >= BUYER_AUDIO_RMS_GATE


def _vad_contains_speech(pcm_bytes: bytes, sample_rate: int) -> bool:
    import webrtcvad

    vad = webrtcvad.Vad(2)
    frame_bytes = int(sample_rate * (VAD_FRAME_MS / 1000.0)) * PCM_SAMPLE_WIDTH * BUYER_AUDIO_CHANNELS
    if frame_bytes <= 0:
        return False

    positive_frames = 0
    total_frames = 0
    for offset in range(0, len(pcm_bytes) - frame_bytes + 1, frame_bytes):
        frame = pcm_bytes[offset: offset + frame_bytes]
        total_frames += 1
        if vad.is_speech(frame, sample_rate):
            positive_frames += 1

    if total_frames == 0:
        return _pcm_rms(pcm_bytes) >= BUYER_AUDIO_RMS_GATE

    return positive_frames >= max(1, math.ceil(total_frames * 0.35))


def _split_agent_speech(text: str) -> list[str]:
    cleaned = " ".join(text.split())
    if not cleaned:
        return []

    sentences = [
        sentence.strip()
        for sentence in re.split(r"(?<=[.!?])\s+", cleaned)
        if sentence.strip()
    ]
    if not sentences:
        return [cleaned]

    segments: list[str] = []
    current = ""
    for sentence in sentences:
        candidate = sentence if not current else f"{current} {sentence}"
        if len(candidate) <= AGENT_TTS_SEGMENT_MAX_CHARS:
            current = candidate
            continue
        if current:
            segments.append(current)
            current = sentence
            continue
        words = sentence.split()
        buffer = ""
        for word in words:
            next_buffer = word if not buffer else f"{buffer} {word}"
            if len(next_buffer) <= AGENT_TTS_SEGMENT_MAX_CHARS:
                buffer = next_buffer
            else:
                if buffer:
                    segments.append(buffer)
                buffer = word
        if buffer:
            segments.append(buffer)
        current = ""

    if current:
        segments.append(current)

    return segments or [cleaned]
