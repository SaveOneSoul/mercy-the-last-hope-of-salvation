"""Gemini editorial adapter for private Ministry content.

Gemini is never the doctrinal authority. It may only improve structure,
readability and pastoral flow of already grounded Catholic content.
"""
import os
import httpx
from fastapi import HTTPException

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip() or "gemini-2.5-flash"
GEMINI_TIMEOUT_SECONDS = float(os.getenv("GEMINI_TIMEOUT_SECONDS", "60"))


def gemini_state() -> dict:
    return {"provider": "Gemini", "configured": bool(GEMINI_API_KEY), "model": GEMINI_MODEL}


def refine_ministry_text(grounded_text: str, *, kind: str, title: str) -> dict:
    if not GEMINI_API_KEY:
        return {"text": grounded_text, "provider": "none", "model": None, "refined": False}
    prompt = f"""You are an editorial assistant, not a doctrinal authority.
Preserve every Catholic doctrinal claim, qualification, citation and source from the grounded text.
Do not add quotations, paragraph numbers, canon numbers, document titles, facts, or theological claims.
Improve only organization, clarity, pastoral flow and readability.
Keep the output suitable for a private {kind} draft titled {title}.
Return only the revised draft.

GROUNDED TEXT:
{grounded_text}"""
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
