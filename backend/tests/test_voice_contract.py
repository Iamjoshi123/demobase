import sys
import types

import pytest

from app.voice.session import VoiceSession, transcribe_audio


@pytest.mark.asyncio
async def test_voice_session_falls_back_to_text_when_disabled(monkeypatch):
    from app.voice import session as voice_module

    monkeypatch.setattr(voice_module.settings, "enable_voice", False)
    voice = VoiceSession("sess-1", "ws-1")

    result = await voice.start()

    assert result["mode"] == "text"
    assert "text chat mode" in result["message"]


@pytest.mark.asyncio
async def test_voice_session_returns_livekit_contract_when_sdk_is_mocked(monkeypatch):
    from app.voice import session as voice_module

    monkeypatch.setattr(voice_module.settings, "enable_voice", True)

    class FakeAccessToken:
        def __init__(self, *args, **kwargs):
            self.identity = None
            self.name = None
            self.grants = None

        def with_identity(self, value):
            self.identity = value
            return self

        def with_name(self, value):
            self.name = value
            return self

        def with_grants(self, grants):
            self.grants = grants
            return self

        def to_jwt(self):
            return "livekit-token"

    fake_livekit = types.SimpleNamespace(
        AccessToken=FakeAccessToken,
        VideoGrants=lambda **kwargs: kwargs,
    )
    livekit_module = types.ModuleType("livekit")
    livekit_module.api = fake_livekit
    monkeypatch.setitem(sys.modules, "livekit", livekit_module)

    voice = VoiceSession("sess-1", "ws-1")
    result = await voice.start()

    assert result["mode"] == "voice"
    assert result["token"] == "livekit-token"
    assert result["room_name"] == "demo-sess-1"


@pytest.mark.asyncio
async def test_transcribe_audio_returns_empty_string_without_whisper(monkeypatch):
    text = await transcribe_audio(b"fake-bytes")

    assert text == ""


@pytest.mark.asyncio
async def test_transcribe_audio_uses_vad_and_language_settings(monkeypatch):
    from app.voice import session as voice_module

    captured = {}

    class FakeSegment:
        text = "Show invoices"

    class FakeModel:
        def transcribe(self, path, **kwargs):
            captured["kwargs"] = kwargs
            return [FakeSegment()], None

    async def fake_get_model():
        return FakeModel()

    monkeypatch.setattr(voice_module, "_get_whisper_model", fake_get_model)

    class FakeTempFile:
        def __init__(self, suffix="", delete=False):
            self.name = "fake.wav"
        def __enter__(self):
            return self
        def __exit__(self, exc_type, exc, tb):
            return False
        def write(self, data):
            return None

    monkeypatch.setattr("tempfile.NamedTemporaryFile", FakeTempFile)
    monkeypatch.setattr("os.unlink", lambda path: None)

    text = await transcribe_audio(b"fake-bytes")

    assert text == "Show invoices"
    assert captured["kwargs"]["vad_filter"] is True
    assert captured["kwargs"]["language"] == voice_module.settings.voice_language
