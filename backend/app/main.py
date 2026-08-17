from __future__ import annotations
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from .settings import settings
from .schemas import ChatRequest, ChatResponse, ContactRequest, ContactResponse
from .ai_service import answer_catholic_question
from .contact_service import process_contact
from .database import init_db
from .rate_limit import SlidingWindowRateLimiter
from .reference_service import retrieve_references
from .recaptcha_service import (
    verify_recaptcha,
    RecaptchaRejected,
    RecaptchaUnavailable,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, version="2.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)
limiter = SlidingWindowRateLimiter(settings.rate_limit_per_minute)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def _require_recaptcha(token: str | None, action: str, request: Request) -> None:
    try:
        verify_recaptcha(token, action, request)
    except RecaptchaRejected:
        # Keep the response intentionally generic; do not leak risk scores or rejection reasons.
        raise HTTPException(status_code=403, detail="Security verification failed.")
    except RecaptchaUnavailable:
        # Fail closed if verification cannot be performed while enforcement is enabled.
        raise HTTPException(
            status_code=503,
            detail="Security verification is temporarily unavailable.",
        )


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": settings.app_name,
        "catholic_only": True,
        "recaptcha_enforced": settings.recaptcha_enforce,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(payload: ChatRequest, request: Request):
    if not limiter.allow("chat:" + _client_key(request)):
        raise HTTPException(status_code=429, detail="Too many requests. Please try again later.")

    _require_recaptcha(payload.recaptcha_token, "chat", request)

    message = payload.message.strip()
    if len(message) > settings.max_chat_chars:
        raise HTTPException(status_code=413, detail="Message is too long.")
    try:
        return answer_catholic_question(message, payload.client_id)
    except Exception:
        # Do not fall back to a general-purpose answer on AI/provider failures.
        raise HTTPException(status_code=503, detail="Catholic AI service is temporarily unavailable.")


@app.get("/api/references")
def references(q: str, request: Request):
    if not limiter.allow("references:" + _client_key(request)):
        raise HTTPException(
            status_code=429,
            detail="Too many requests. Please try again later.",
        )

    query = q.strip()
    if len(query) < 2 or len(query) > settings.max_chat_chars:
        raise HTTPException(
            status_code=400,
            detail="Query must be between 2 and the configured maximum characters.",
        )

    return {
        "query": query,
        "references": retrieve_references(query, limit=6),
    }


@app.post("/api/contact", response_model=ContactResponse)
def contact(payload: ContactRequest, request: Request):
    if not limiter.allow("contact:" + _client_key(request)):
        raise HTTPException(status_code=429, detail="Too many submissions. Please try again later.")

    _require_recaptcha(payload.recaptcha_token, "contact", request)

    if len(payload.message) > settings.max_contact_chars:
        raise HTTPException(status_code=413, detail="Message is too long.")
    reply, delivered_to_owner, stored = process_contact(payload)
    if not (delivered_to_owner or stored):
        raise HTTPException(
            status_code=503,
            detail=(
                "Contact delivery is not configured yet. Configure owner email/WhatsApp "
                "or a durable database before accepting submissions."
            ),
        )
    return ContactResponse(
        accepted=True,
        message="Your message has been received.",
        automatic_reply=reply,
        delivered_to_owner=delivered_to_owner,
        stored=stored,
    )
