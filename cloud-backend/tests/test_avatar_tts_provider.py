"""Contract tests for provider-neutral Mercy Avatar TTS."""
import base64

import pytest

from app import avatar_tts


def test_tts_disabled_by_default(monkeypatch):
    monkeypatch.delenv("AVATAR_TTS_PROVIDER", raising=False)
    monkeypatch.delenv("MERCY_VOICE_URL", raising=False)
    assert avatar_tts.tts_provider() == "none"
    assert avatar_tts.tts_enabled() is False
    assert avatar_tts.tts_status_label() == "browser_speech_synthesis_when_supported"


def test_mercy_voice_requires_https(monkeypatch):
    monkeypatch.setenv("AVATAR_TTS_PROVIDER", "mercy_voice")
    monkeypatch.setenv("MERCY_VOICE_URL", "http://voice.internal")
    assert avatar_tts.tts_enabled() is False
    assert avatar_tts._mercy_voice_url() is None


def test_valid_audio_normalizes_timing():
    encoded = base64.b64encode(b"test-audio").decode("ascii")
    result = avatar_tts._valid_audio(
        {
            "audio_base64": encoded,
            "mime_type": "audio/wav",
            "timings": [
                {"token": "Peace", "start": 0, "end": 0.4},
                {"token": "bad", "start": 1, "end": 0.5},
            ],
        },
        "Mercy Voice",
    )
    assert result is not None
    assert result["provider"] == "Mercy Voice"
    assert result["mime_type"] == "audio/wav"
    assert result["timings"] == [{"c": "Peace", "start": 0.0, "end": 0.4}]


@pytest.mark.asyncio
async def test_disabled_synthesis_makes_no_provider_call(monkeypatch):
    monkeypatch.setenv("AVATAR_TTS_PROVIDER", "none")

    class ForbiddenClient:
        def __init__(self, *args, **kwargs):
            raise AssertionError("provider client must not be created when TTS is disabled")

    monkeypatch.setattr(avatar_tts.httpx, "AsyncClient", ForbiddenClient)
    assert await avatar_tts.synthesize_with_timing("Peace be with you.", "en") is None


def test_mercy_voice_iam_mode_is_enabled_for_https_url(monkeypatch):
    monkeypatch.setenv("AVATAR_TTS_PROVIDER", "mercy_voice")
    monkeypatch.setenv("MERCY_VOICE_URL", "https://voice.example.run.app")
    monkeypatch.setenv("MERCY_VOICE_AUTH_MODE", "cloud_run_iam")
    assert avatar_tts.tts_enabled() is True


def test_mercy_voice_invalid_auth_mode_fails_closed(monkeypatch):
    monkeypatch.setenv("AVATAR_TTS_PROVIDER", "mercy_voice")
    monkeypatch.setenv("MERCY_VOICE_URL", "https://voice.example.run.app")
    monkeypatch.setenv("MERCY_VOICE_AUTH_MODE", "unexpected")
    assert avatar_tts.tts_enabled() is False
