import os
import time
from collections import defaultdict, deque
from threading import Lock

import httpx
from fastapi import HTTPException
from pydantic import BaseModel, Field

MAGISTERIUM_API_KEY = os.getenv("MAGISTERIUM_API_KEY", "").strip()
MAGISTERIUM_MODEL = os.getenv("MAGISTERIUM_MODEL", "magisterium-1").strip() or "magisterium-1"
MAGISTERIUM_CHAT_URL = os.getenv(
    "MAGISTERIUM_CHAT_URL",
    "https://www.magisterium.com/api/v1/chat/completions",
).strip()
MAGISTERIUM_TIMEOUT_SECONDS = float(os.getenv("MAGISTERIUM_TIMEOUT_SECONDS", "30"))
MAGISTERIUM_RATE_LIMIT_PER_MINUTE = max(1, int(os.getenv("MAGISTERIUM_RATE_LIMIT_PER_MINUTE", "8")))

SYSTEM_PROMPT = """You are the Catholic AI service for Mercy – The Last Hope of Salvation.
Answer questions concerning the Roman Catholic faith: Sacred Scripture in Catholic context, the Catechism, Magisterium, councils and papal teaching, canon law, sacraments, liturgy, moral theology, prayer, saints, Church Fathers, Catholic spirituality, Divine Mercy, evangelization and Catholic Charismatic Renewal.
For requests unrelated to the Catholic faith or the mission of this Catholic website, politely state that this assistant is limited to Catholic questions.
Distinguish clearly between binding doctrine, Church discipline, theological opinion, devotional practice and private revelation. Never present private revelation as completing or replacing the public Revelation fulfilled in Jesus Christ.
Prefer primary and authoritative Catholic sources. Do not invent quotations, paragraph numbers, canon numbers, document titles or attributions.
When the user writes in Khasi, answer in clear Khasi when you can do so accurately. Preserve established Catholic, biblical and theological terms when a confident Khasi equivalent is unavailable rather than inventing terminology. If accurate Khasi expression is not possible, say briefly that you are answering that part in English for accuracy.
For confession, canonical cases, medical emergencies, mental-health crises, legal questions or other high-stakes personal situations, provide general Catholic information but direct the user to an appropriate priest, confessor, canon lawyer or qualified professional as applicable.
Keep answers pastoral, precise and faithful to Catholic teaching."""


class CatholicChatIn(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    language: str = Field(default="en", pattern="^(en|kha)$")


_rate_events: dict[str, deque[float]] = defaultdict(deque)
_rate_lock = Lock()


def magisterium_state() -> dict:
    return {
        "provider": "Magisterium AI",
        "configured": bool(MAGISTERIUM_API_KEY),
        "model": MAGISTERIUM_MODEL,
    }


def allow_request(client_key: str) -> bool:
    now = time.monotonic()
    cutoff = now - 60.0
    key = client_key or "unknown"
    with _rate_lock:
        q = _rate_events[key]
        while q and q[0] < cutoff:
            q.popleft()
        if len(q) >= MAGISTERIUM_RATE_LIMIT_PER_MINUTE:
            return False
        q.append(now)
        return True


def _message_content(data: dict) -> str:
    try:
        content = data["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return ""
    if isinstance(content, str):
        return content.strip()
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, dict):
                text = item.get("text") or item.get("content")
                if isinstance(text, str) and text.strip():
                    parts.append(text.strip())
        return "\n\n".join(parts).strip()
    return ""


def _citation_sources(data: dict) -> list[dict]:
    sources: list[dict] = []
    seen: set[tuple[str, str, str]] = set()
    for index, citation in enumerate(data.get("citations") or [], start=1):
        if not isinstance(citation, dict):
            continue
        title = str(citation.get("document_title") or citation.get("cited_text_heading") or "Catholic source").strip()
        authority = str(citation.get("document_author") or "Catholic source").strip()
        url = str(citation.get("source_url") or "").strip()
        reference = str(citation.get("document_reference") or "").strip()
        year = citation.get("document_year")
        if year and str(year) not in title:
            display_title = f"{title} ({year})"
        else:
            display_title = title
        fingerprint = (url, display_title, reference)
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        sources.append(
            {
                "id": f"mag-{index}",
                "title": display_title,
                "authority": authority,
                "url": url,
                "reference": reference,
            }
        )
    return sources[:10]


def ask_magisterium(payload: CatholicChatIn, client_key: str = "unknown") -> dict:
    if not MAGISTERIUM_API_KEY:
        raise HTTPException(status_code=503, detail="magisterium_not_configured")
    if not allow_request(client_key):
        raise HTTPException(status_code=429, detail="mercy_ai_rate_limit")

    language_note = (
        "The user selected Khasi. Prefer a faithful Khasi answer, while retaining technical Catholic terms when needed."
        if payload.language == "kha"
        else "The user selected English. Answer in English."
    )
    body = {
        "model": MAGISTERIUM_MODEL,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "system", "content": language_note},
            {"role": "user", "content": payload.message.strip()},
        ],
        "stream": False,
        "return_related_questions": True,
    }
    headers = {
        "Authorization": f"Bearer {MAGISTERIUM_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }

    try:
        with httpx.Client(timeout=MAGISTERIUM_TIMEOUT_SECONDS) as client:
            response = client.post(MAGISTERIUM_CHAT_URL, headers=headers, json=body)
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="magisterium_timeout") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="magisterium_unavailable") from exc

    if response.status_code == 429:
        raise HTTPException(status_code=429, detail="magisterium_rate_limit")
    if response.status_code in (401, 403):
        raise HTTPException(status_code=503, detail="magisterium_authentication_failed")
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="magisterium_upstream_error")

    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="magisterium_invalid_response") from exc

    reply = _message_content(data)
    if not reply:
        raise HTTPException(status_code=502, detail="magisterium_empty_response")

    related = [
        str(q).strip()
        for q in (data.get("related_questions") or [])
        if isinstance(q, str) and q.strip()
    ][:5]
    return {
        "reply": reply,
        "scope": "catholic",
        "provider": "Magisterium AI",
        "model": MAGISTERIUM_MODEL,
        "sources": _citation_sources(data),
        "related_questions": related,
        "needs_human_follow_up": False,
    }
