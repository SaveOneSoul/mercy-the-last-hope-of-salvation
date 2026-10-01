"""Lazy, process-cached Kokoro adapter.

Kokoro is loaded only when MERCY_VOICE_ENGINE=kokoro. The pipeline is cached
per container process so repeated synthesis requests do not repeatedly
initialize the model. Khasi is intentionally not routed here.
"""
from __future__ import annotations

import base64
from functools import lru_cache
import io
import logging
import os

logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _kokoro_pipeline():
    from kokoro import KPipeline

    return KPipeline(lang_code="a")


def synthesize_kokoro(text: str, requested_voice: str) -> dict | None:
    try:
        import soundfile as sf
    except ImportError:
        logger.exception("Kokoro synthesis dependency import failed")
        return None

    voice = os.getenv("MERCY_KOKORO_VOICE", "af_heart").strip() or "af_heart"
    # Public callers cannot select arbitrary model artifacts; operator config wins.
    try:
        pipeline = _kokoro_pipeline()
        chunks = []
        for _graphemes, _phonemes, audio in pipeline(text[:5000], voice=voice):
            chunks.append(audio)
        if not chunks:
            logger.error("Kokoro synthesis produced no audio chunks")
            return None

        import numpy as np
        samples = np.concatenate(chunks)
        buf = io.BytesIO()
        sf.write(buf, samples, 24000, format="WAV", subtype="PCM_16")
    except Exception as exc:
        # Do not log user text, request payloads, credentials, or model tokens.
        logger.error(
            "Kokoro synthesis failed: %s: %s",
            type(exc).__name__,
            str(exc)[:300],
        )
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
