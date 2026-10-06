"""Gemini ministry contributor for private Catholic Ministry drafts.

Gemini contributes independently to structure, biblical/historical context and
pastoral development. Magisterium-grounded material remains the doctrinal
authority whenever the providers differ.
"""
import os
import httpx
from fastapi import HTTPException

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "60"))


def gemini_state() -> dict:
    return {"provider": "Gemini", "configured": bool(GEMINI_API_KEY), "model": GEMINI_MODEL}


def refine_ministry_text(grounded_text: str, *, kind: str, title: str, request_text: str = "") -> dict:
    if not GEMINI_API_KEY:
        return {"text": grounded_text, "provider": "none", "model": None, "refined": False}
    prompt = f"""You are the pastoral and homiletic contributor in a Catholic ministry system.
You are not the final doctrinal authority. Answer the ministry request yourself and contribute
biblical context, historical/cultural background, structure, pastoral application, reflection,
prayer, and clear presentation. For a homily, respect the Catholic liturgical character and the
Holy See Homiletic Directory (2014): proclaimed Scripture, liturgical celebration and season,
the Paschal Mystery, sound Catholic doctrine, and the needs of the assembly.
Do not invent quotations, Scripture references, Catechism/canon numbers, Vatican citations,
Fathers, or saints. If your proposal differs from the Magisterium-grounded contribution below,
preserve the Magisterium-grounded doctrine and sources.

TYPE: {kind}
TITLE: {title}
REQUEST:
{request_text}

MAGISTERIUM-GROUNDED CONTRIBUTION:
{grounded_text}

Return one integrated private draft using both contributions."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent"
    try:
        with httpx.Client(timeout=httpx.Timeout(GEMINI_TIMEOUT_SECONDS, connect=15.0)) as client:
            response = client.post(url, params={"key": GEMINI_API_KEY}, json={
                "contents": [{"parts": [{"text": prompt}]}],
                "generationConfig": {"temperature": 0.2}
            })
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="gemini_timeout") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="gemini_unavailable") from exc
    if response.status_code in (401, 403):
        raise HTTPException(status_code=503, detail="gemini_authentication_failed")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="gemini_upstream_error")
    try:
        data = response.json()
        text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (ValueError, KeyError, IndexError, TypeError, AttributeError) as exc:
        raise HTTPException(status_code=502, detail="gemini_invalid_response") from exc
    if not text:
        raise HTTPException(status_code=502, detail="gemini_empty_response")
    return {"text": text, "provider": "Gemini", "model": GEMINI_MODEL, "refined": True}
