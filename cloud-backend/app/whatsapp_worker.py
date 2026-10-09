"""Conservative WhatsApp outbox dispatcher.

This module deliberately does not retry ambiguous provider failures automatically:
an HTTP timeout may mean Meta accepted the message. An operator must reconcile it.
Run the worker explicitly after Meta onboarding; no background scheduler is enabled.
"""
import os
import secrets
from datetime import datetime, timezone

import httpx
from sqlalchemy import select

from .db import SessionLocal
from .whatsapp_ministry import WhatsAppConversation, WhatsAppInbound, WhatsAppOutbox
from .whatsapp_delivery import WELCOME, outbound_ready, send_text


def dispatch_one():
    """Claim one welcome with a DB transaction, then attempt delivery once.

    Status 'sending' survives crashes to prevent duplicate sends after uncertain
    outcomes. An operator must reconcile sending/unknown rows with Meta receipts.
    """
    if not outbound_ready():
        return {"status": "disabled"}
    with SessionLocal.begin() as db:
        stmt = (select(WhatsAppOutbox)
                .where(WhatsAppOutbox.kind == "welcome",
                       WhatsAppOutbox.status == "pending")
                .order_by(WhatsAppOutbox.id)
                .with_for_update(skip_locked=True).limit(1))
        job = db.scalar(stmt)
        if job is None:
            return {"status": "empty"}
        inbound = db.get(WhatsAppInbound, job.inbound_id)
        conversation = db.scalar(select(WhatsAppConversation).where(
            WhatsAppConversation.account_id == inbound.account_id,
            WhatsAppConversation.contact_id == inbound.contact_id).with_for_update())
        # Only send from the explicitly onboarded Meta phone number.
        if (conversation is None or conversation.handoff or
                inbound.account_id != os.environ["WHATSAPP_PHONE_NUMBER_ID"]):
            job.status = "suppressed"
            return {"status": "suppressed"}
        job_id = job.id
        recipient = inbound.contact_id
        job.status = "sending"

    try:
        receipt = send_text(recipient, WELCOME)
        if not receipt or not receipt[0].get("id"):
            raise ValueError("provider_receipt_missing")
    except (httpx.HTTPError, ValueError, RuntimeError):
        with SessionLocal.begin() as db:
            job = db.get(WhatsAppOutbox, job_id)
            if job.status == "sending":
                job.status = "unknown"
        return {"status": "unknown", "job_id": job_id}

    with SessionLocal.begin() as db:
        job = db.get(WhatsAppOutbox, job_id)
        if job.status == "sending":
            job.status = "sent"
    return {"status": "sent", "job_id": job_id}


def worker_authorized(supplied: str) -> bool:
    secret = os.getenv("WHATSAPP_WORKER_SECRET", "")
    return bool(secret and secrets.compare_digest(secret, supplied))
