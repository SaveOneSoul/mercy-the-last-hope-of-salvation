"""Contract tests for disabled outbound transport and owner-only workflow."""
from app.whatsapp_delivery import outbound_ready, WELCOME, MENU

def test_outbound_remains_disabled_without_explicit_flag(monkeypatch):
    monkeypatch.delenv("WHATSAPP_OUTBOUND_ENABLED", raising=False)
    assert not outbound_ready()

def test_outbound_requires_credentials(monkeypatch):
    monkeypatch.setenv("WHATSAPP_OUTBOUND_ENABLED", "true")
    monkeypatch.delenv("WHATSAPP_ACCESS_TOKEN", raising=False)
    assert not outbound_ready()

def test_ministry_copy_and_menu():
    assert "Jesus Christ" in WELCOME
    assert "homiletics.html" in MENU
    assert "HUMAN" in MENU
