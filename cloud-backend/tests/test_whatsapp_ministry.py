"""Decision-contract tests for the WhatsApp greeting foundation."""
from datetime import datetime, timedelta, timezone

from app.whatsapp_ministry import should_welcome

NOW = datetime(2026, 10, 9, tzinfo=timezone.utc)

def test_first_contact():
    assert should_welcome(None, NOW, False)
    assert not should_welcome(None, NOW, True)

def test_exact_seven_day_boundary():
    assert not should_welcome(NOW - timedelta(hours=167, minutes=59), NOW, True)
    assert should_welcome(NOW - timedelta(hours=168), NOW, True)
    assert should_welcome(NOW - timedelta(days=8), NOW, True)

def test_alternate_day_activity_and_handoff():
    assert not should_welcome(NOW - timedelta(days=2), NOW, True)
    assert not should_welcome(NOW - timedelta(days=9), NOW, True, handoff=True)
