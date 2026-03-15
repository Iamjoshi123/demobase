import asyncio

import pytest

from app.live import media
from app.live import realtime_voice
from app.voice import session as voice_session
from app.config import settings


def test_trim_silence_removes_leading_and_trailing_quiet_frames():
    loud = (1000).to_bytes(2, "little", signed=True)
    quiet = (0).to_bytes(2, "little", signed=True)
    raw = quiet * 20 + loud * 10 + quiet * 20

    trimmed = media._trim_silence(raw, threshold=1)

    assert trimmed.startswith(loud)
    assert trimmed.endswith(loud)
    assert len(trimmed) == len(loud) * 10


def test_pcm_rms_gate_filters_quiet_chunks():
    quiet = (0).to_bytes(2, "little", signed=True) * 40
    loud = (600).to_bytes(2, "little", signed=True) * 40

    assert media._pcm_rms(quiet) < media.BUYER_AUDIO_RMS_GATE
    assert media._pcm_rms(loud) > media.BUYER_AUDIO_RMS_GATE


@pytest.mark.asyncio
async def test_get_whisper_model_is_cached(monkeypatch):
    created = []

    class FakeModel:
        pass

    def fake_whisper_model(name, device, compute_type):
        created.append((name, device, compute_type))
        return FakeModel()

    monkeypatch.setattr(voice_session, "_whisper_model", None)

    class FakeModule:
        WhisperModel = staticmethod(fake_whisper_model)

    import builtins

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "faster_whisper":
            return FakeModule()
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)

    first = await voice_session._get_whisper_model()
    second = await voice_session._get_whisper_model()

    assert first is second
    assert created == [(settings.voice_whisper_model, "cpu", "int8")]


@pytest.mark.asyncio
async def test_queue_transcription_skips_when_one_is_already_in_flight():
    publisher = media.LiveKitBrowserPublisher()
    calls = []
    forwarded = []

    async def fake_forward(text: str) -> None:
        forwarded.append(text)

    async def fake_transcribe(pcm_bytes: bytes, sample_rate: int) -> str:
        calls.append((pcm_bytes, sample_rate))
        await asyncio.sleep(0.05)
        return "show me invoices"

    publisher._on_transcript = fake_forward
    publisher._transcribe_pcm = fake_transcribe

    loud_chunk = (900).to_bytes(2, "little", signed=True) * 200
    publisher._queue_transcription(loud_chunk, media.BUYER_AUDIO_SAMPLE_RATE)
    await asyncio.sleep(0)
    publisher._queue_transcription(loud_chunk, media.BUYER_AUDIO_SAMPLE_RATE)

    await asyncio.sleep(0.08)

    assert len(calls) == 1
    assert forwarded == ["show me invoices"]


@pytest.mark.asyncio
async def test_barge_in_interrupts_queued_agent_audio():
    publisher = media.LiveKitBrowserPublisher()

    class FakeAudioSource:
        def __init__(self) -> None:
            self.clear_calls = 0

        def clear_queue(self) -> None:
            self.clear_calls += 1

    publisher._audio_source = FakeAudioSource()
    publisher._speak_task = asyncio.create_task(asyncio.sleep(10))

    loud_frame = (900).to_bytes(2, "little", signed=True) * 40
    publisher._maybe_interrupt_for_barge_in(loud_frame)
    await asyncio.sleep(0)

    assert publisher._audio_source.clear_calls == 1
    assert publisher._speak_task.cancelled() is True


@pytest.mark.asyncio
async def test_barge_in_notifies_speech_activity_callback():
    publisher = media.LiveKitBrowserPublisher()
    activity_calls = []

    class FakeAudioSource:
        def clear_queue(self) -> None:
            return None

    async def on_activity() -> None:
        activity_calls.append("speaking")

    publisher._audio_source = FakeAudioSource()
    publisher._on_speech_activity = on_activity
    loud_frame = (900).to_bytes(2, "little", signed=True) * 40

    publisher._maybe_interrupt_for_barge_in(loud_frame)
    await asyncio.sleep(0)

    assert activity_calls == ["speaking"]


def test_should_consume_audio_track_only_for_buyer_audio():
    publisher = media.LiveKitBrowserPublisher()

    class Publication:
        def __init__(self, name: str):
            self.name = name

    class Participant:
        def __init__(self, identity: str):
            self.identity = identity

    assert publisher._should_consume_audio_track(Publication("microphone"), Participant("buyer-123")) is True
    assert publisher._should_consume_audio_track(Publication("agent-audio"), Participant("agent-123")) is False
    assert publisher._should_consume_audio_track(Publication("microphone"), Participant("agent-123")) is False


def test_chunk_contains_speech_falls_back_to_rms_when_vad_unavailable(monkeypatch):
    real_import = __import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "webrtcvad":
            raise ImportError("missing")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr("builtins.__import__", fake_import)

    loud = (800).to_bytes(2, "little", signed=True) * 200
    quiet = (0).to_bytes(2, "little", signed=True) * 200

    assert media._chunk_contains_speech(loud, media.BUYER_AUDIO_SAMPLE_RATE) is True
    assert media._chunk_contains_speech(quiet, media.BUYER_AUDIO_SAMPLE_RATE) is False


def test_vad_contains_speech_uses_majority_speech_frames(monkeypatch):
    class FakeVad:
        def __init__(self, aggressiveness: int) -> None:
            self.calls = 0

        def is_speech(self, frame: bytes, sample_rate: int) -> bool:
            self.calls += 1
            return self.calls <= 3

    monkeypatch.setitem(__import__("sys").modules, "webrtcvad", type("FakeModule", (), {"Vad": FakeVad}))

    frame_bytes = int(media.BUYER_AUDIO_SAMPLE_RATE * (media.VAD_FRAME_MS / 1000.0)) * media.PCM_SAMPLE_WIDTH
    pcm = b"\x01\x00" * (frame_bytes // 2) * 5

    assert media._vad_contains_speech(pcm, media.BUYER_AUDIO_SAMPLE_RATE) is True


def test_split_agent_speech_breaks_long_reply_into_incremental_segments():
    text = (
        "Welcome to the product demo. "
        "I will show the dashboard first. "
        "Then I will open invoices and explain how payment reminders, client follow-ups, aging summaries, "
        "and payment link workflows fit into your finance handoff. "
        "After that, I will show how the product keeps customer communication and collections aligned."
    )

    segments = media._split_agent_speech(text)

    assert len(segments) >= 2
    assert all(len(segment) <= media.AGENT_TTS_SEGMENT_MAX_CHARS for segment in segments)
    assert segments[0].startswith("Welcome to the product demo.")


def test_create_media_publisher_uses_openai_realtime_when_enabled(monkeypatch):
    monkeypatch.setattr(settings, "app_env", "development")
    monkeypatch.setattr(settings, "enable_voice", True)
    monkeypatch.setattr(settings, "voice_provider", "openai_realtime")
    monkeypatch.setattr(settings, "openai_api_key", "test-key")

    publisher = media.create_media_publisher()

    assert isinstance(publisher, media.OpenAIRealtimeMediaPublisher)


def test_realtime_transcript_filter_drops_repetition():
    transcript, reason = realtime_voice._sanitize_realtime_transcript(
        "yeah yeah yeah yeah yeah",
        last_transcript="",
        last_timestamp=0.0,
        min_chars=2,
    )

    assert transcript == ""
    assert reason == "repetitive"


def test_realtime_transcript_filter_drops_immediate_duplicate():
    transcript, reason = realtime_voice._sanitize_realtime_transcript(
        "Show invoices",
        last_transcript="Show invoices",
        last_timestamp=__import__("time").monotonic(),
        min_chars=2,
    )

    assert transcript == ""
    assert reason == "duplicate"


def test_realtime_transcript_filter_keeps_non_latin_text():
    transcript, reason = realtime_voice._sanitize_realtime_transcript(
        "???????",
        last_transcript="",
        last_timestamp=0.0,
        min_chars=2,
    )

    assert transcript
    assert reason is None


@pytest.mark.asyncio
async def test_realtime_bridge_speak_sends_response_request(monkeypatch):
    sent_messages = []
    incoming = asyncio.Queue()

    class FakeWebSocket:
        async def send(self, payload: str) -> None:
            sent_messages.append(payload)
            if '"type": "response.create"' in payload:
                await incoming.put('{"type":"response.done"}')

        def __aiter__(self):
            return self

        async def __anext__(self):
            return await incoming.get()

        async def close(self) -> None:
            return None

    async def fake_connect(*args, **kwargs):
        return FakeWebSocket()

    bridge = realtime_voice.OpenAIRealtimeVoiceBridge(
        on_audio_chunk=lambda chunk: asyncio.sleep(0),
        websocket_factory=fake_connect,
    )

    monkeypatch.setattr(settings, "openai_api_key", "test-key")
    monkeypatch.setattr(settings, "openai_realtime_model", "gpt-realtime")
    monkeypatch.setattr(settings, "openai_realtime_voice", "alloy")
    monkeypatch.setattr(settings, "openai_realtime_transcription_model", "gpt-4o-mini-transcribe")
    monkeypatch.setattr(settings, "openai_realtime_silence_ms", 280)
    try:
        await incoming.put('{"type":"session.created"}')
        await bridge.start()
        await bridge.speak("Welcome to the demo.")
    finally:
        await bridge.stop()

    assert any('"type": "session.update"' in payload for payload in sent_messages)
    assert any('"type": "response.create"' in payload for payload in sent_messages)


@pytest.mark.asyncio
async def test_consume_audio_track_flushes_after_short_silence(monkeypatch):
    publisher = media.LiveKitBrowserPublisher()
    queued: list[tuple[int, int]] = []

    class FakeFrame:
        def __init__(self, amplitude: int, samples_per_channel: int) -> None:
            sample = amplitude.to_bytes(2, "little", signed=True)
            self.data = sample * samples_per_channel
            self.samples_per_channel = samples_per_channel

    class FakeAudioStream:
        def __init__(self, track, sample_rate, num_channels) -> None:
            self._events = [
                FakeFrame(900, 1600),
                FakeFrame(900, 1600),
                FakeFrame(900, 1600),
                FakeFrame(0, 1600),
                FakeFrame(0, 1600),
                FakeFrame(0, 1600),
            ]

        def __aiter__(self):
            async def _iterator():
                for event in self._events:
                    yield event
            return _iterator()

    publisher._rtc = type("FakeRtc", (), {"AudioStream": FakeAudioStream})
    publisher._queue_transcription = lambda pcm_bytes, sample_rate: queued.append((len(pcm_bytes), sample_rate))

    await publisher._consume_audio_track(object())

    assert len(queued) == 1
    assert queued[0][1] == media.BUYER_AUDIO_SAMPLE_RATE
