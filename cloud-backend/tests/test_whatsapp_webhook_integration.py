"""Webhook integration contracts; run with a disposable PostgreSQL DATABASE_URL."""
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.db import Base, SessionLocal, engine
from app.main import app
from app.whatsapp_ministry import WhatsAppInbound, WhatsAppOutbox, WhatsAppConversation

pytestmark = pytest.mark.skipif(
    engine.dialect.name != "postgresql" or os.getenv("WHATSAPP_TEST_DATABASE") != "1",
    reason="requires disposable PostgreSQL and WHATSAPP_TEST_DATABASE=1",
)

@pytest.fixture
def client(monkeypatch):
    monkeypatch.setenv("WHATSAPP_APP_SECRET", "integration-secret-only")
    monkeypatch.setenv("WHATSAPP_VERIFY_TOKEN", "integration-verify-only")
    Base.metadata.create_all(engine)
    with SessionLocal.begin() as db:
        db.query(WhatsAppOutbox).delete()
        db.query(WhatsAppInbound).delete()
        db.query(WhatsAppConversation).delete()
    yield TestClient(app)


def signed(client, payload, signature=True):
    raw = json.dumps(payload).encode()
    digest = hmac.new(b"integration-secret-only", raw, hashlib.sha256).hexdigest()
    return client.post("/api/whatsapp/webhook", content=raw, headers={
        "x-hub-signature-256": "sha256=" + (digest if signature else "bad")})


def event(msg_id, timestamp, contact="15550001111"):
    return {"object": "whatsapp_business_account", "entry": [{"changes": [{
        "value": {"metadata": {"phone_number_id": "phone-test"}, "messages": [{
            "id": msg_id, "from": contact, "timestamp": str(int(timestamp.timestamp())),
            "type": "text", "text": {"body": "Peace be with you"}}]}}]}]}


def test_webhook_verification_and_signature(client):
    assert client.get("/api/whatsapp/webhook", params={
        "hub.mode": "subscribe", "hub.verify_token": "integration-verify-only",
        "hub.challenge": "12345"}).text == "12345"
    assert client.get("/api/whatsapp/webhook", params={
        "hub.mode": "subscribe", "hub.verify_token": "wrong",
        "hub.challenge": "12345"}).status_code == 403
    assert signed(client, event("invalid-signature", datetime.now(timezone.utc)), False).status_code == 401


def test_persist_deduplicate_and_suppress_out_of_order(client):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    first = event("first", now - timedelta(days=2))
    assert signed(client, first).status_code == 200
    assert signed(client, first).status_code == 200
    assert signed(client, event("older", now - timedelta(days=3))).status_code == 200
    assert signed(client, event("recent", now)).status_code == 200
    with SessionLocal() as db:
        inbound = db.scalars(select(WhatsAppInbound)).all()
        welcomes = db.scalars(select(WhatsAppOutbox).where(WhatsAppOutbox.kind == "welcome")).all()
        notifications = db.scalars(select(WhatsAppOutbox).where(WhatsAppOutbox.kind == "owner_notification")).all()
        assert len(inbound) == 3
        assert len(welcomes) == 1
        assert len(notifications) == 3
        assert db.scalar(select(WhatsAppConversation)).last_human_at == now


def test_handoff_suppresses_welcome(client):
    now = datetime.now(timezone.utc).replace(microsecond=0)
    with SessionLocal.begin() as db:
        db.add(WhatsAppConversation(account_id="phone-test", contact_id="15550001111", handoff=True))
    assert signed(client, event("handoff-msg", now)).status_code == 200
    with SessionLocal() as db:
        assert db.scalar(select(WhatsAppOutbox).where(WhatsAppOutbox.kind == "welcome")) is None
