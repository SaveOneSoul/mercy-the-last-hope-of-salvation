"""Lazy Kokoro adapter.

Kokoro is loaded only when MERCY_VOICE_ENGINE=kokoro. This keeps contract tests
lightweight and prevents model downloads/imports when the engine is disabled.
Khasi is intentionally not routed here.
"""
from __future__ import annotations

import base64
import io
import os

def synthesize_kokoro(text: str, requested_voice: str) -> dict | None:
    try:
        import soundfile as sf
        from kokoro import KPipeline
    except ImportError:
        return None

    voice = os.getenv("MERCY_KOKORO_VOICE", "af_heart").strip() or "af_heart"
    # Public callers cannot select arbitrary model artifacts; operator config wins.
    try:
        pipeline = KPipeline(lang_code="a")
        chunks = []
        for _graphemes, _phonemes, audio in pipeline(text[:5000], voice=voice):
            chunks.append(audio)
        if not chunks:
            return None

        import numpy as np
        samples = np.concatenate(chunks)
        buf = io.BytesIO()
        sf.write(buf, samples, 24000, format="WAV", subtype="PCM_16")
    except Exception:
        return None

    return {
        "provider": "Mercy Voice",
        "engine": "kokoro",
        "voice": voice,
        "mime_type": "audio/wav",
        "audio_base64": base64.b64encode(buf.getvalue()).decode("ascii"),
        # Kokoro exposes grapheme/phoneme chunks, not stable character timestamps.
        # Frontend lip motion therefore uses its existing best-effort fallback.
        "timings": [],
    }
