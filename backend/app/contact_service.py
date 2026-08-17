from __future__ import annotations
from .schemas import ContactRequest
from .database import save_contact_message
from .notifications import send_email, send_whatsapp_text
from .ai_service import answer_catholic_question
from .settings import settings


def _fixed_ack(topic: str, name: str) -> str:
    first = name.strip().split()[0] if name.strip() else "friend"
    t = topic.lower()
    if "prayer" in t:
        return (
            f"Dear {first}, thank you for entrusting your prayer intention to Mercy – The Last Hope of Salvation. "
            "Your message has been received. May the Lord Jesus surround you with His mercy and peace."
        )
    if "testimony" in t:
        return (
            f"Dear {first}, thank you for sharing your testimony with Mercy – The Last Hope of Salvation. "
            "Your message has been received and will be reviewed with gratitude and discretion."
        )
    return (
        f"Dear {first}, thank you for contacting Mercy – The Last Hope of Salvation. "
        "Your message has been received and will be reviewed. May the peace of Christ be with you."
    )


def process_contact(payload: ContactRequest) -> tuple[str, bool, bool]:
    automatic_reply = _fixed_ack(payload.topic, payload.name)
    if settings.auto_reply_faith_questions and "faith question" in payload.topic.lower():
        result = answer_catholic_question(payload.message, client_id=str(payload.email or payload.phone or ""))
        automatic_reply = result.reply

    stored = save_contact_message(
        name=payload.name,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        topic=payload.topic,
        message=payload.message,
        automatic_reply=automatic_reply,
    )

    owner_body = (
        f"New website message\n\nName: {payload.name}\nEmail: {payload.email or ''}\n"
        f"Phone/WhatsApp: {payload.phone or ''}\nTopic: {payload.topic}\n\nMessage:\n{payload.message}\n\n"
        f"Automatic reply:\n{automatic_reply}"
    )

    delivered_to_owner = False
    if settings.owner_email:
        try:
            delivered_to_owner = send_email(
                settings.owner_email,
                f"[Mercy Website] {payload.topic} — {payload.name}",
                owner_body,
            ) or delivered_to_owner
        except Exception:
            pass

    if settings.owner_whatsapp:
        try:
            delivered_to_owner = send_whatsapp_text(settings.owner_whatsapp, owner_body) or delivered_to_owner
        except Exception:
            pass

    # Do not tell the visitor their request was accepted unless we either delivered it
    # to the owner or stored it durably.
    accepted = delivered_to_owner or stored
    if accepted:
        if payload.email:
            try:
                send_email(str(payload.email), "Mercy – The Last Hope of Salvation: message received", automatic_reply)
            except Exception:
                pass
        if payload.phone:
            try:
                send_whatsapp_text(payload.phone, automatic_reply)
            except Exception:
                pass

    return automatic_reply, delivered_to_owner, stored
