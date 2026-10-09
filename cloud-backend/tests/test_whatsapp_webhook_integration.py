"""Webhook integration contracts; run with a disposable PostgreSQL DATABASE_URL."""
import hashlib
import hmac
import json
import os
from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, text, inspect

from app.db import Base, SessionLocal, engine
from app.main import app
from app.whatsapp_ministry import WhatsAppInbound, WhatsAppOutbox, WhatsAppConversation, purge_expired_messages

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


def test_existing_mercy_tables_survive_repeat_schema_creation(client):
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE IF NOT EXISTS whatsapp_migration_sentinel (id integer PRIMARY KEY, note text)"))
        connection.execute(text("INSERT INTO whatsapp_migration_sentinel (id, note) VALUES (1, 'preserve') ON CONFLICT (id) DO NOTHING"))
    Base.metadata.create_all(engine)
    Base.metadata.create_all(engine)
    assert inspect(engine).has_table("whatsapp_ministry_inbound")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT note FROM whatsapp_migration_sentinel WHERE id=1")).scalar_one() == "preserve"


def test_retention_keeps_pending_and_removes_terminal(client):
    old = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(days=45)
    with SessionLocal.begin() as db:
        db.add_all([
            WhatsAppInbound(account_id="phone-test", contact_id="one", message_id="retained", received_at=old),
            WhatsAppInbound(account_id="phone-test", contact_id="two", message_id="purged", received_at=old),
        ])
        db.flush()
        rows = {x.message_id: x for x in db.scalars(select(WhatsAppInbound)).all()}
        db.add_all([
            WhatsAppOutbox(inbound_id=rows["retained"].id, kind="owner_notification", status="pending"),
            WhatsAppOutbox(inbound_id=rows["purged"].id, kind="owner_notification", status="acknowledged"),
        ])
    with SessionLocal.begin() as db:
        assert purge_expired_messages(db, now=datetime.now(timezone.utc)) == 1
    with SessionLocal() as db:
        assert [x.message_id for x in db.scalars(select(WhatsAppInbound)).all()] == ["retained"]


def test_outbound_defaults_to_disabled(monkeypatch):
    from app.whatsapp_delivery import send_text, outbound_ready
    monkeypatch.delenv("WHATSAPP_OUTBOUND_ENABLED", raising=False)
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-only")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "phone-test")
    assert not outbound_ready()
    with pytest.raises(RuntimeError, match="whatsapp_outbound_disabled"):
        send_text("15550001111", "test")


def test_worker_sends_once_and_never_retries_ambiguous_receipt(client, monkeypatch):
    from app import whatsapp_worker
    now = datetime.now(timezone.utc).replace(microsecond=0)
    assert signed(client, event("worker-first", now)).status_code == 200
    monkeypatch.setenv("WHATSAPP_OUTBOUND_ENABLED", "true")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-only")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "phone-test")
    sent = []
    monkeypatch.setattr(whatsapp_worker, "send_text", lambda contact, body: sent.append(contact) or [{"id": "meta-test-1"}])
    assert whatsapp_worker.dispatch_one()["status"] == "sent"
    assert whatsapp_worker.dispatch_one()["status"] == "empty"
    assert len(sent) == 1


def test_worker_suppresses_handoff_and_stale_pending_welcome(client, monkeypatch):
    from app import whatsapp_worker
    now = datetime.now(timezone.utc).replace(microsecond=0)
    assert signed(client, event("worker-first", now - timedelta(days=2))).status_code == 200
    # Simulate a queued delivery that has aged beyond the 24-hour service window.
    with SessionLocal.begin() as db:
        inbound = db.scalar(select(WhatsAppInbound).where(WhatsAppInbound.message_id == "worker-first"))
        inbound.received_at = now - timedelta(days=2)
    monkeypatch.setenv("WHATSAPP_OUTBOUND_ENABLED", "true")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-only")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "phone-test")
    monkeypatch.setattr(whatsapp_worker, "send_text", lambda *args: pytest.fail("must not send stale greeting"))
    assert whatsapp_worker.dispatch_one()["status"] == "suppressed"


def test_worker_unknown_receipt_never_automatically_retries(client, monkeypatch):
    from app import whatsapp_worker
    now = datetime.now(timezone.utc).replace(microsecond=0)
    assert signed(client, event("worker-first", now)).status_code == 200
    monkeypatch.setenv("WHATSAPP_OUTBOUND_ENABLED", "true")
    monkeypatch.setenv("WHATSAPP_ACCESS_TOKEN", "test-only")
    monkeypatch.setenv("WHATSAPP_PHONE_NUMBER_ID", "phone-test")
    sent = []
    def ambiguous(*args):
        sent.append(1)
        raise RuntimeError("simulated uncertain provider result")
    monkeypatch.setattr(whatsapp_worker, "send_text", ambiguous)
    assert whatsapp_worker.dispatch_one()["status"] == "unknown"
    assert whatsapp_worker.dispatch_one()["status"] == "empty"
    assert len(sent) == 1
