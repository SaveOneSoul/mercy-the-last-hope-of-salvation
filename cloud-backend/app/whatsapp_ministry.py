"""WhatsApp Divine Mercy webhook foundation.

Inbound events are persisted before acknowledgement. No outbound messages are sent
until a separate delivery worker is configured and reviewed.
"""
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, select
from sqlalchemy.orm import Mapped, Session, mapped_column
from pydantic import BaseModel

from .cms_admin import require_admin, _require_write_guard

from .db import Base, SessionLocal

router = APIRouter(prefix="/api/whatsapp", tags=["divine-mercy-whatsapp"])
INACTIVITY = timedelta(hours=168)

class WhatsAppConversation(Base):
    __tablename__ = "whatsapp_ministry_conversations"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(String(120))
    contact_id: Mapped[str] = mapped_column(String(120))
    last_human_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    handoff: Mapped[bool] = mapped_column(default=False)
    history_known: Mapped[bool] = mapped_column(default=False)
    __table_args__ = (UniqueConstraint("account_id", "contact_id"),)

class WhatsAppInbound(Base):
    __tablename__ = "whatsapp_ministry_inbound"
    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[str] = mapped_column(String(120))
    message_id: Mapped[str] = mapped_column(String(200))
    contact_id: Mapped[str] = mapped_column(String(120))
    body: Mapped[str] = mapped_column(Text, default="")
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    __table_args__ = (UniqueConstraint("account_id", "message_id"),)

class WhatsAppOutbox(Base):
    __tablename__ = "whatsapp_ministry_outbox"
    id: Mapped[int] = mapped_column(primary_key=True)
    inbound_id: Mapped[int] = mapped_column(ForeignKey("whatsapp_ministry_inbound.id"))
    kind: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(24), default="pending")
    __table_args__ = (UniqueConstraint("inbound_id", "kind"),)

def should_welcome(previous, now, history_known, handoff=False):
    if handoff:
        return False
    if previous is None:
        return not history_known
    if previous.tzinfo is None:
        previous = previous.replace(tzinfo=timezone.utc)
    return now - previous >= INACTIVITY

def _verify(raw, signature):
    secret = os.getenv("WHATSAPP_APP_SECRET", "")
    if not secret:
        raise HTTPException(503, "whatsapp_not_configured")
    expected = "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    if not hmac.compare_digest(expected, signature):
        raise HTTPException(401, "invalid_whatsapp_signature")

@router.get("/webhook")
def verify_webhook(request: Request):
    token = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
    params = request.query_params
    if not token:
        raise HTTPException(503, "whatsapp_not_configured")
    if params.get("hub.mode") != "subscribe" or not hmac.compare_digest(params.get("hub.verify_token", ""), token):
        raise HTTPException(403, "verification_failed")
    return PlainTextResponse(params.get("hub.challenge", ""))

@router.post("/webhook")
async def receive_webhook(request: Request):
    raw = await request.body()
    _verify(raw, request.headers.get("x-hub-signature-256", ""))
    if len(raw) > 1024 * 1024:
        raise HTTPException(413, "payload_too_large")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeDecodeError):
        raise HTTPException(400, "invalid_payload")
    if payload.get("object") != "whatsapp_business_account":
        return {"accepted": True}
    with SessionLocal() as db:
        for entry in payload.get("entry", []):
            for change in entry.get("changes", []):
                value = change.get("value", {})
                account = str(value.get("metadata", {}).get("phone_number_id", ""))[:120]
                if not account:
                    continue
                for message in value.get("messages", []):
                    msg_id = str(message.get("id", ""))[:200]
                    contact = str(message.get("from", ""))[:120]
                    if not msg_id or not contact:
                        continue
                    # Lock per-contact state for concurrent webhook deliveries.
                    with db.begin():
                        from sqlalchemy import text
                        if db.bind.dialect.name == "postgresql":
                            key = hashlib.sha256((account + ":" + contact).encode()).digest()
                            lock_id = int.from_bytes(key[:8], "big", signed=True)
                            db.execute(text("SELECT pg_advisory_xact_lock(:key)"), {"key": lock_id})
                        duplicate = db.scalar(select(WhatsAppInbound.id).where(
                            WhatsAppInbound.account_id == account, WhatsAppInbound.message_id == msg_id))
                        if duplicate:
                            continue
                        now = datetime.now(timezone.utc)
                        conversation = db.scalar(select(WhatsAppConversation).where(
                            WhatsAppConversation.account_id == account,
                            WhatsAppConversation.contact_id == contact).with_for_update())
                        if conversation is None:
                            conversation = WhatsAppConversation(account_id=account, contact_id=contact)
                            db.add(conversation)
                            db.flush()
                        # The message is persisted even when human handoff suppresses bot replies.
                        body = message.get("text", {}).get("body", "") if message.get("type") == "text" else ""
                        inbound = WhatsAppInbound(account_id=account, message_id=msg_id,
                            contact_id=contact, body=str(body)[:10000], received_at=now)
                        db.add(inbound)
                        db.flush()
                        db.add(WhatsAppOutbox(inbound_id=inbound.id, kind="owner_notification"))
                        if should_welcome(conversation.last_human_at, now, conversation.history_known, conversation.handoff):
                            db.add(WhatsAppOutbox(inbound_id=inbound.id, kind="welcome"))
                        if conversation.last_human_at is None or now > conversation.last_human_at.replace(
                            tzinfo=conversation.last_human_at.tzinfo or timezone.utc):
                            conversation.last_human_at = now
                        conversation.history_known = True
    return {"accepted": True}


# Owner-only inbox and takeover. These endpoints never expose private messages
# to unauthenticated callers and never authorize ministry draft generation.
class HandoffIn(BaseModel):
    enabled: bool

@router.get("/admin/conversations")
def list_conversations(session: dict = Depends(require_admin)):
    with SessionLocal() as db:
        rows = db.scalars(select(WhatsAppConversation).order_by(
            WhatsAppConversation.id.desc()).limit(100)).all()
        return {"items": [{"id": row.id, "account_id": row.account_id,
                           "contact_id": row.contact_id, "handoff": row.handoff,
                           "last_human_at": row.last_human_at} for row in rows]}

@router.get("/admin/conversations/{conversation_id}/messages")
def list_messages(conversation_id: int, session: dict = Depends(require_admin)):
    with SessionLocal() as db:
        row = db.get(WhatsAppConversation, conversation_id)
        if row is None:
            raise HTTPException(404, "conversation_not_found")
        messages = db.scalars(select(WhatsAppInbound).where(
            WhatsAppInbound.account_id == row.account_id,
            WhatsAppInbound.contact_id == row.contact_id
        ).order_by(WhatsAppInbound.id.desc()).limit(100)).all()
        return {"items": [{"id": m.id, "body": m.body, "received_at": m.received_at}
                          for m in reversed(messages)]}

@router.put("/admin/conversations/{conversation_id}/handoff")
def change_handoff(conversation_id: int, payload: HandoffIn,
                   request: Request, session: dict = Depends(require_admin)):
    _require_write_guard(request, session)
    with SessionLocal.begin() as db:
        row = db.scalar(select(WhatsAppConversation).where(
            WhatsAppConversation.id == conversation_id).with_for_update())
        if row is None:
            raise HTTPException(404, "conversation_not_found")
        row.handoff = payload.enabled
        if payload.enabled:
            pending = db.scalars(select(WhatsAppOutbox).join(
                WhatsAppInbound, WhatsAppOutbox.inbound_id == WhatsAppInbound.id
            ).where(WhatsAppInbound.account_id == row.account_id,
                    WhatsAppInbound.contact_id == row.contact_id,
                    WhatsAppOutbox.kind == "welcome",
                    WhatsAppOutbox.status == "pending")).all()
            for item in pending:
                item.status = "suppressed"
    return {"handoff": payload.enabled}
