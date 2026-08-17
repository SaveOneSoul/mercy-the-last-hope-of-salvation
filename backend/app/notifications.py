from __future__ import annotations
import smtplib
from email.message import EmailMessage
import httpx
from .settings import settings


def email_ready() -> bool:
    return bool(settings.smtp_host and settings.smtp_from)


def whatsapp_ready() -> bool:
    return bool(settings.whatsapp_api_url and settings.whatsapp_access_token)


def owner_delivery_configured() -> bool:
    return bool((settings.owner_email and email_ready()) or (settings.owner_whatsapp and whatsapp_ready()))


def send_email(to_address: str, subject: str, body: str) -> bool:
    if not (email_ready() and to_address):
        return False
    msg = EmailMessage()
    msg["From"] = settings.smtp_from
    msg["To"] = to_address
    msg["Subject"] = subject
    msg.set_content(body)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as smtp:
        if settings.smtp_use_tls:
            smtp.starttls()
        if settings.smtp_username:
            smtp.login(settings.smtp_username, settings.smtp_password)
        smtp.send_message(msg)
    return True


def send_whatsapp_text(to_number: str, body: str) -> bool:
    """Send text through a configured Meta WhatsApp Cloud API messages endpoint."""
    if not (whatsapp_ready() and to_number):
        return False
    headers = {
        "Authorization": f"Bearer {settings.whatsapp_access_token}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "type": "text",
        "text": {"body": body[:4000]},
    }
    with httpx.Client(timeout=20) as client:
        response = client.post(settings.whatsapp_api_url, headers=headers, json=payload)
        response.raise_for_status()
    return True
