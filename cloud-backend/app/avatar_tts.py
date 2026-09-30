"""Optional ElevenLabs TTS adapter for Mercy Avatar.

Disabled by default. Secrets remain server-side. Returns audio plus character timing
when ElevenLabs is configured; callers should fall back to browser speech otherwise.
"""
from __future__ import annotations

import base64
import os

import httpx


def tts_enabled() -> bool:
    return (
        os.getenv("AVATAR_TTS_PROVIDER","none").strip().lower()=="elevenlabs"
        and bool(os.getenv("ELEVENLABS_API_KEY","").strip())
        and bool(os.getenv("ELEVENLABS_VOICE_ID","").strip())
    )


async def synthesize_with_timing(text: str) -> dict | None:
    if not tts_enabled():
        return None
    key=os.getenv("ELEVENLABS_API_KEY","").strip()
    voice=os.getenv("ELEVENLABS_VOICE_ID","").strip()
    model=os.getenv("ELEVENLABS_MODEL_ID","eleven_multilingual_v2").strip()
    url=f"https://api.elevenlabs.io/v1/text-to-speech/{voice}/with-timestamps"
    payload={
        "text": text[:5000],
        "model_id": model,
        "voice_settings": {
            "stability": float(os.getenv("ELEVENLABS_STABILITY","0.62")),
            "similarity_boost": float(os.getenv("ELEVENLABS_SIMILARITY","0.78")),
            "style": float(os.getenv("ELEVENLABS_STYLE","0.18")),
            "use_speaker_boost": True,
        },
    }
    headers={"xi-api-key":key,"Content-Type":"application/json"}
    try:
        async with httpx.AsyncClient(timeout=45.0,follow_redirects=False) as client:
            r=await client.post(url,json=payload,headers=headers)
            r.raise_for_status()
            data=r.json()
    except (httpx.HTTPError,ValueError,TypeError):
        return None

    audio_b64=str(data.get("audio_base64","")).strip()
    alignment=data.get("alignment") or data.get("normalized_alignment") or {}
    chars=alignment.get("characters") or []
    starts=alignment.get("character_start_times_seconds") or []
    ends=alignment.get("character_end_times_seconds") or []
    timings=[]
    for i,ch in enumerate(chars[:6000]):
        if i>=len(starts) or i>=len(ends):
            break
        try:
            timings.append({"c":str(ch)[:1],"start":float(starts[i]),"end":float(ends[i])})
        except (TypeError,ValueError):
            continue
    if not audio_b64:
        return None
    try:
        base64.b64decode(audio_b64,validate=True)
    except Exception:
        return None
    return {
        "provider":"ElevenLabs",
        "mime_type":"audio/mpeg",
        "audio_base64":audio_b64,
        "timings":timings,
    }
