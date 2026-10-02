"""Mercy Voice Service: private synthesis boundary for the Mercy Avatar.

The service intentionally keeps the engine behind a small contract so model
selection can change after licensing, quality, and Khasi evaluation.
"""
from __future__ import annotations

import base64
import io
import math
import os
import struct
import wave

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .engines import synthesize_kokoro

app = FastAPI(title="Mercy Voice Service", version="0.1.0")


class SynthesisIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)
    language: str = Field(default="en", pattern="^(en|kha)$")
    voice: str = Field(default="mercy-female-v1", max_length=80)
    return_timing: bool = True


def _authorized(authorization: str | None) -> bool:
    # In Cloud Run IAM mode, Google authenticates the caller before the request
    # reaches this container. Keep application bearer-token auth for local or
    # non-IAM deployments only.
    auth_mode = os.getenv("MERCY_VOICE_AUTH_MODE", "token").strip().lower()
    if auth_mode == "cloud_run_iam":
        return True
    if auth_mode == "token":
        token = os.getenv("MERCY_VOICE_SERVICE_TOKEN", "").strip()
        return bool(token) and authorization == f"Bearer {token}"
    if auth_mode == "none":
        return os.getenv("MERCY_VOICE_ALLOW_UNAUTHENTICATED", "false").lower() == "true"
    return False


def _placeholder_wav(text: str) -> str:
    """Generate a short non-speech WAV used only for contract validation."""
    rate = 16000
    duration = min(0.35 + len(text) * 0.003, 1.25)
    frames = int(rate * duration)
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(rate)
        for i in range(frames):
            # Quiet confirmation tone: never presented as real speech.
            sample = int(700 * math.sin(2 * math.pi * 220 * i / rate))
            wav.writeframesraw(struct.pack("<h", sample))
    return base64.b64encode(buf.getvalue()).decode("ascii")


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "mercy-voice",
        "engine": os.getenv("MERCY_VOICE_ENGINE", "contract_only"),
        "languages": ["en", "kha"],
        "khasi_status": "corpus_evaluation_required",
    }


@app.post("/v1/synthesize")
def synthesize(payload: SynthesisIn, authorization: str | None = Header(default=None)) -> dict:
    if not _authorized(authorization):
        raise HTTPException(status_code=401, detail="unauthorized")

    engine = os.getenv("MERCY_VOICE_ENGINE", "contract_only").strip().lower()
    if engine == "contract_only":
        if os.getenv("MERCY_VOICE_ENABLE_CONTRACT_AUDIO", "false").lower() != "true":
            raise HTTPException(status_code=503, detail="tts_engine_not_configured")
        return {
            "provider": "Mercy Voice",
            "engine": "contract_only",
            "synthetic_test_audio": True,
            "mime_type": "audio/wav",
            "audio_base64": _placeholder_wav(payload.text),
            "timings": [],
        }

    if engine == "kokoro":
        if payload.language != "en":
            raise HTTPException(status_code=422, detail="language_not_supported_by_engine")
        result = synthesize_kokoro(payload.text, payload.voice)
        if result is None:
            raise HTTPException(status_code=503, detail="tts_engine_unavailable")
        return result

    raise HTTPException(status_code=503, detail="tts_engine_not_available")
