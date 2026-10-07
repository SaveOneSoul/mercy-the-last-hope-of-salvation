import hashlib
import hmac
import os
import time
import unittest
from unittest.mock import patch

from fastapi import HTTPException

from app.ministry_bridge import _authenticate, _seen_nonces


class MinistryBridgeSecurityTest(unittest.TestCase):
    def setUp(self):
        _seen_nonces.clear()

    def _headers(self, body=b'{"kind":"seminar"}', nonce="n-1", timestamp=None):
        timestamp = timestamp or str(int(time.time()))
        sig = hmac.new(
            b"bridge-test-secret",
            timestamp.encode() + b"." + nonce.encode() + b"." + body,
            hashlib.sha256,
        ).hexdigest()
        return timestamp, nonce, "sha256=" + sig

    @patch.dict(os.environ, {"MINISTRY_BRIDGE_SECRET": "bridge-test-secret"}, clear=False)
    def test_valid_signature_is_accepted(self):
        body = b'{"kind":"seminar"}'
        _authenticate(body, *self._headers(body))

    @patch.dict(os.environ, {"MINISTRY_BRIDGE_SECRET": "bridge-test-secret"}, clear=False)
    def test_bad_signature_fails_closed(self):
        with self.assertRaises(HTTPException) as caught:
            _authenticate(b"{}", str(int(time.time())), "n-2", "sha256=bad")
        self.assertEqual(caught.exception.status_code, 401)

    @patch.dict(os.environ, {"MINISTRY_BRIDGE_SECRET": "bridge-test-secret"}, clear=False)
    def test_stale_request_is_rejected(self):
        body = b"{}"
        ts = str(int(time.time()) - 301)
        sig = hmac.new(b"bridge-test-secret", ts.encode() + b".n-3." + body, hashlib.sha256).hexdigest()
        with self.assertRaises(HTTPException) as caught:
            _authenticate(body, ts, "n-3", "sha256=" + sig)
        self.assertEqual(caught.exception.status_code, 401)

    @patch.dict(os.environ, {"MINISTRY_BRIDGE_SECRET": "bridge-test-secret"}, clear=False)
    def test_nonce_replay_is_rejected(self):
        body = b"{}"
        args = self._headers(body, "n-replay")
        _authenticate(body, *args)
        with self.assertRaises(HTTPException) as caught:
            _authenticate(body, *args)
        self.assertEqual(caught.exception.status_code, 409)


if __name__ == "__main__":
    unittest.main()
