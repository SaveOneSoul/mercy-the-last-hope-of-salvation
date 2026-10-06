import unittest
from types import SimpleNamespace
from unittest.mock import patch

from fastapi import HTTPException

from app.ai_ministry import GenerateIn, TransitionIn, _owner_identity, _require, _transition


class FakeDB:
    def __init__(self, row=None): self.row = row
    def get(self, _model, _id): return self.row
    def commit(self): pass
    def refresh(self, _row): pass


class MinistryApiPolicyTest(unittest.TestCase):
    def test_admin_session_maps_to_authenticated_owner_not_phone(self):
        identity = _owner_identity({"csrf": "x"})
        self.assertTrue(identity.authenticated)
        self.assertEqual(identity.channel, "web")
        self.assertIn("owner", identity.roles)

    def test_unknown_action_not_implicitly_granted_to_member(self):
        identity = _require({"csrf": "x"}, "publish")
        self.assertIn("ministry:publish", identity.permissions)

    @patch("app.ai_ministry._require_write_guard")
    def test_publish_requires_reviewed_state(self, _guard):
        row = SimpleNamespace(id=1, owner_subject="mercy-owner", kind="homily", title="x",
            content="x", sources_json="[]", status="draft", version=1,
            created_at=None, updated_at=None, published_at=None)
        with self.assertRaises(HTTPException) as caught:
            _transition(1, TransitionIn(expected_version=1), SimpleNamespace(), {"csrf": "x"}, FakeDB(row), "published")
        self.assertEqual(caught.exception.status_code, 409)

    @patch("app.ai_ministry._require_write_guard")
    def test_optimistic_lock_blocks_stale_publish(self, _guard):
        row = SimpleNamespace(id=1, owner_subject="mercy-owner", kind="homily", title="x",
            content="x", sources_json="[]", status="reviewed", version=2,
            created_at=None, updated_at=None, published_at=None)
        with self.assertRaises(HTTPException) as caught:
            _transition(1, TransitionIn(expected_version=1), SimpleNamespace(), {"csrf": "x"}, FakeDB(row), "published")
        self.assertEqual(caught.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
