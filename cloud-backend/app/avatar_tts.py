"""Provider-neutral speech synthesis adapter for Mercy Avatar.

TTS is disabled by default. Provider credentials remain server-side. The public
/avatar/speak contract is stable: providers return audio plus optional character
or phoneme timing, while callers retain browser speech as a fallback.

Supported providers:
- elevenlabs: optional hosted adapter retained for compatibility.
- mercy_voice: private self-hosted Mercy Voice service.

Mercy Voice is deliberately a separate service so neural model/runtime choices
can evolve without coupling a large TTS stack to the main Mercy API.
"""
from __future__ import annotations

import base64
import os
from urllib.parse import urlparse

import httpx


_SUPPORTED_PROVIDERS = {"elevenlabs", "mercy_voice"}


def tts_provider() -> str:
    provider = os.getenv("AVATAR_TTS_PROVIDER", "none").strip().lower()
    return provider if provider in _SUPPORTED_PROVIDERS else "none"


def tts_enabled() -> bool:
    provider = tts_provider()
    if provider == "elevenlabs":
        return bool(
            os.getenv("ELEVENLABS_API_KEY", "").strip()
            and os.getenv("ELEVENLABS_VOICE_ID", "").strip()
        )
    if provider == "mercy_voice":
        return bool(os.getenv("MERCY_VOICE_URL", "").strip())
    return False


def tts_status_label() -> str:
    provider = tts_provider()
    if provider == "mercy_voice" and tts_enabled():
        return "mercy_voice_with_browser_fallback"
    if provider == "elevenlabs" and tts_enabled():
        return "elevenlabs_with_browser_fallback"
    return "browser_speech_synthesis_when_supported"


def _valid_audio(data: dict, provider: str) -> dict | None:
    audio_b64 = str(data.get("audio_base64", "")).strip()
    if not audio_b64:
        return None
    try:
        base64.b64decode(audio_b64, validate=True)
    except Exception:
        return None

    raw_timings = data.get("timings") or []
    timings = []
    if isinstance(raw_timings, list):
        for item in raw_timings[:6000]:
            if not isinstance(item, dict):
                continue
            try:
                start = float(item.get("start"))
                end = float(item.get("end"))
            except (TypeError, ValueError):
                continue
            if start < 0 or end < start:
                continue
            token = str(item.get("c", item.get("token", "")))[:8]
            timings.append({"c": token, "start": start, "end": end})

    mime_type = str(data.get("mime_type", "audio/mpeg")).strip().lower()
    if mime_type not in {"audio/mpeg", "audio/wav", "audio/ogg"}:
        return None
    return {
        "provider": provider,
        "mime_type": mime_type,
        "audio_base64": audio_b64,
        "timings": timings,
    }


async def _synthesize_elevenlabs(text: str) -> dict | None:
    key = os.getenv("ELEVENLABS_API_KEY", "").strip()
    voice = os.getenv("ELEVENLABS_VOICE_ID", "").strip()
    if not key or not voice:
        return None
    model = os.getenv("ELEVENLABS_MODEL_ID", "eleven_multilingual_v2").strip()
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps"
    payload = {
        "text": text[:5000],
        "model_id": model,
        "voice_settings": {
            "stability": float(os.getenv("ELEVENLABS_STABILITY", "0.62")),
            "similarity_boost": float(os.getenv("ELEVENLABS_SIMILARITY", "0.78")),
            "style": float(os.getenv("ELEVENLABS_STYLE", "0.18")),
            "use_speaker_boost": True,
        },
    }
    try:
        async with httpx.AsyncClient(timeout=45.0, follow_redirects=False) as client:
            response = await client.post(
                url,
                json=payload,
                headers={"xi-api-key": key, "Content-Type": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return None

    alignment = data.get("alignment") or data.get("normalized_alignment") or {}
    chars = alignment.get("characters") or []
    starts = alignment.get("character_start_times_seconds") or []
    ends = alignment.get("character_end_times_seconds") or []
    timings = []
    for index, char in enumerate(chars[:6000]):
        if index >= len(starts) or index >= len(ends):
            break
        try:
            timings.append(
                {"c": str(char)[:1], "start": float(starts[index]), "end": float(ends[index])}
            )
        except (TypeError, ValueError):
            continue
    data["timings"] = timings
    data["mime_type"] = "audio/mpeg"
    return _valid_audio(data, "ElevenLabs")


def _mercy_voice_url() -> str | None:
    base = os.getenv("MERCY_VOICE_URL", "").strip().rstrip("/")
    if not base:
        return None
    parsed = urlparse(base)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        return None
    return base + "/v1/synthesize"


async def _synthesize_mercy_voice(text: str, language: str) -> dict | None:
    url = _mercy_voice_url()
    if not url:
        return None
    token = os.getenv("MERCY_VOICE_TOKEN", "").strip()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    payload = {
        "text": text[:5000],
        "language": "kha" if language == "kha" else "en",
        "voice": os.getenv("MERCY_VOICE_ID", "mercy-female-v1").strip() or "mercy-female-v1",
        "return_timing": True,
    }
    timeout = max(5.0, min(float(os.getenv("MERCY_VOICE_TIMEOUT_SECONDS", "45")), 120.0))
    try:
        async with httpx.AsyncClient(timeout=timeout, follow_redirects=False) as client:
            response = await client.post(url, json=payload, headers=headers)
            response.raise_for_status()
            data = response.json()
    except (httpx.HTTPError, ValueError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return _valid_audio(data, "Mercy Voice")


async def synthesize_with_timing(text: str, language: str = "en") -> dict | None:
    if not tts_enabled():
        return None
    provider = tts_provider()
    if provider == "mercy_voice":
        return await _synthesize_mercy_voice(text, language)
    if provider == "elevenlabs":
        return await _synthesize_elevenlabs(text)
    return None
