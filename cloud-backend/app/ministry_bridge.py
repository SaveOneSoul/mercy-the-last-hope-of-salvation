"""Private machine-to-machine bridge for Catholic AI Ministry.

HMAC-authenticated, short-lived requests with nonce replay protection. This route
has no public navigation and does not reuse browser admin sessions.
"""
import hashlib
import hmac
import os
import time
from collections import OrderedDict
from threading import Lock

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from .ai_ministry import GenerateIn, _orchestrate_ministry

router = APIRouter(prefix="/api/private/ministry-bridge", tags=["private-ai-ministry-bridge"])
_MAX_SKEW_SECONDS = 300
_MAX_NONCES = 4096
_seen_nonces = OrderedDict()
_nonce_lock = Lock()


class BridgeIn(BaseModel):
    kind: str = Field(max_length=40)
    title: str = Field(min_length=1, max_length=240)
    request: str = Field(min_length=2, max_length=5000)


def _authenticate(raw: bytes, timestamp: str, nonce: str, signature: str) -> None:
    secret = os.getenv("MINISTRY_BRIDGE_SECRET", "").strip()
    if not secret:
        raise HTTPException(status_code=503, detail="ministry_bridge_not_configured")
    try:
        sent_at = int(timestamp)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="ministry_bridge_unauthorized")
    if abs(int(time.time()) - sent_at) > _MAX_SKEW_SECONDS:
        raise HTTPException(status_code=401, detail="ministry_bridge_unauthorized")
    if not nonce or len(nonce) > 96:
        raise HTTPException(status_code=401, detail="ministry_bridge_unauthorized")
    expected = hmac.new(
        secret.encode("utf-8"),
        timestamp.encode("ascii") + b"." + nonce.encode("utf-8") + b"." + raw,
        hashlib.sha256,
    ).hexdigest()
    supplied = signature.removeprefix("sha256=").lower()
    if not supplied or not hmac.compare_digest(expected, supplied):
        raise HTTPException(status_code=401, detail="ministry_bridge_unauthorized")
    now = int(time.time())
    with _nonce_lock:
        expired = [key for key, value in _seen_nonces.items() if now - value > _MAX_SKEW_SECONDS]
        for key in expired:
            _seen_nonces.pop(key, None)
        if nonce in _seen_nonces:
            raise HTTPException(status_code=409, detail="ministry_bridge_replay")
        _seen_nonces[nonce] = now
        while len(_seen_nonces) > _MAX_NONCES:
            _seen_nonces.popitem(last=False)


@router.post("/generate")
async def bridge_generate(request: Request):
    raw = await request.body()
    _authenticate(
        raw,
        request.headers.get("x-ministry-timestamp", ""),
        request.headers.get("x-ministry-nonce", ""),
        request.headers.get("x-ministry-signature", ""),
    )
    try:
        incoming = BridgeIn.model_validate_json(raw)
    except Exception:
        raise HTTPException(status_code=422, detail="invalid_ministry_request")
    result = _orchestrate_ministry(
        GenerateIn(kind=incoming.kind, title=incoming.title, request=incoming.request),
        "whatsapp-owner",
    )
    return {"kind": incoming.kind, "title": incoming.title.strip(), **result}
