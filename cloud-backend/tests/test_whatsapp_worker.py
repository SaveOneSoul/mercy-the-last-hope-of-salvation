"""No-send safety tests for the conservative outbox dispatcher."""
from app.whatsapp_worker import dispatch_one, worker_authorized


def test_worker_does_not_touch_db_when_disabled(monkeypatch):
    monkeypatch.delenv("WHATSAPP_OUTBOUND_ENABLED", raising=False)
    assert dispatch_one() == {"status": "disabled"}


def test_worker_secret_required(monkeypatch):
    monkeypatch.delenv("WHATSAPP_WORKER_SECRET", raising=False)
    assert not worker_authorized("")
    assert not worker_authorized("anything")


def test_worker_secret_compared(monkeypatch):
    monkeypatch.setenv("WHATSAPP_WORKER_SECRET", "test-only-secret")
    assert worker_authorized("test-only-secret")
    assert not worker_authorized("wrong")
