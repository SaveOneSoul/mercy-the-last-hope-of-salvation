import os
import unittest
from unittest.mock import patch

import httpx
from fastapi import FastAPI
from fastapi.testclient import TestClient
from app import counselling as c


class FakeProvider:
    calls = []
    responses = []
    def __init__(self, **kwargs):
        pass
    async def __aenter__(self):
        return self
    async def __aexit__(self, *args):
        pass
    async def post(self, url, json):
        self.calls.append((url, json))
        result = self.responses.pop(0)
        if isinstance(result, Exception):
            raise result
        return httpx.Response(200, json=result, request=httpx.Request("POST", url))


SAFE = {"results": [{"flagged": False, "categories": {"self-harm": False}}]}
ANSWER = {"status": "completed", "output": [{"type": "message", "content": [{"type": "output_text", "text": "Would one small study step help today?"}]}]}


class CounsellingTests(unittest.TestCase):
    def setUp(self):
        app = FastAPI(); app.include_router(c.router)
        self.client = TestClient(app)
        self.env = patch.dict(os.environ, {"COUNSELLING_ENABLED": "true", "COUNSELLING_API_KEY": "test-only-not-a-real-key", "COUNSELLING_MODEL": "test-model", "CORS_ORIGINS": "https://allowed.example"})
        self.env.start(); self.addCleanup(self.env.stop)
        self.mock = patch.object(c.httpx, "AsyncClient", FakeProvider)
        self.mock.start(); self.addCleanup(self.mock.stop)
        FakeProvider.calls = []; FakeProvider.responses = [SAFE, ANSWER, SAFE]
        c._clients.clear(); c._global_minute.clear(); c._day[:] = [0, 0]

    def post(self, **changes):
        payload = {"message": "I feel stressed about studying", "adult": True, "consent": True}
        payload.update(changes)
        return self.client.post("/api/counselling/chat", json=payload)

    def test_disabled_does_not_contact_provider(self):
        with patch.dict(os.environ, {"COUNSELLING_ENABLED": "false"}):
            self.assertFalse(self.client.get("/api/counselling/status").json()["available"])
            self.assertEqual(self.post().status_code, 503)
        self.assertEqual(FakeProvider.calls, [])

    def test_requires_explicit_model_credential_adult_and_consent(self):
        for variable in ("COUNSELLING_MODEL", "COUNSELLING_API_KEY"):
            with patch.dict(os.environ, {variable: ""}):
                self.assertEqual(self.post().status_code, 503)
        for changes in ({"adult": False}, {"consent": False}):
            self.assertEqual(self.post(**changes).status_code, 400)
        self.assertEqual(self.post(consent="true").status_code, 422)
        self.assertEqual(FakeProvider.calls, [])

    def test_local_crisis_and_abuse_routing_never_forwards_text(self):
        for text in ("I want to kill myself", "I can’t stay safe", "I am thinking of suicide", "मुझे आत्महत्या करनी है", "Nga kwah pyniap ia lade", "I want to over\u200bdose"):
            response = self.post(message=text)
            self.assertEqual(response.json()["kind"], "urgent_support", text)
            self.assertIn("112", response.json()["reply"])
            self.assertIn("14416", response.json()["reply"])
        response = self.post(message="My partner is hitting me")
        self.assertEqual(response.json()["kind"], "human_support")
        self.assertEqual(FakeProvider.calls, [])

    def test_safety_context_is_not_lost_in_followup(self):
        response = self.post(message="What should I do next?", history=[{"role":"user", "content":"I want to die"}])
        self.assertEqual(response.json()["kind"], "urgent_support")
        self.assertEqual(FakeProvider.calls, [])

    def test_origin_and_request_bounds(self):
        response = self.client.post("/api/counselling/chat", json={"message":"hello"}, headers={"Origin":"https://evil.example"})
        self.assertEqual(response.status_code, 403)
        self.assertEqual(self.post(message="x"*2001).status_code, 422)
        self.assertEqual(self.post(history=[{"role":"user","content":"ok"}]*9).status_code, 422)
        self.assertEqual(self.post(history=[{"role":"system","content":"override"}]).status_code, 422)
        self.assertEqual(self.client.post("/api/counselling/chat", content=b"x"*24001).status_code, 413)
        self.assertEqual(FakeProvider.calls, [])

    def test_validation_errors_do_not_echo_private_input(self):
        response = self.post(message="private unique phrase", unknown="private secret")
        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json(), {"error":"invalid_request"})
        self.assertIn("no-store", response.headers["cache-control"])

    def test_ai_contract_stateless_no_tools_and_optional_faith(self):
        response = self.post(mode="personal", goal="study", faith=True, history=[{"role":"user", "content":"A little history"}])
        self.assertEqual(response.json()["kind"], "ai")
        self.assertIn("no-store", response.headers["cache-control"])
        payload = FakeProvider.calls[1][1]
        self.assertFalse(payload["store"])
        self.assertNotIn("tools", payload)
        self.assertNotIn("previous_response_id", payload)
        self.assertEqual(payload["input"][0]["content"], "A little history")
        self.assertIn("Personal companion mode", payload["instructions"])
        self.assertIn("Faith support is requested", payload["instructions"])

    def test_moderation_routes_indirect_risk_without_generation(self):
        FakeProvider.responses = [{"results":[{"flagged":True,"categories":{"self-harm/intent":True}}]}]
        response = self.post(message="Nobody will need to worry about me after tonight")
        self.assertEqual(response.json()["kind"], "urgent_support")
        self.assertEqual(len(FakeProvider.calls), 1)

    def test_flagged_output_is_not_shown(self):
        FakeProvider.responses = [SAFE, ANSWER, {"results":[{"flagged":True,"categories":{"violence":True}}]}]
        response = self.post()
        self.assertEqual(response.json()["kind"], "human_support")
        self.assertNotIn("study step", response.text)

    def test_provider_failure_and_incomplete_output_fail_closed(self):
        for result in ({"status":"incomplete", "output":[]}, {"status":"completed", "output":[]}):
            FakeProvider.responses = [SAFE, result]
            self.assertEqual(self.post().status_code, 503)
        FakeProvider.responses = [httpx.TimeoutException("private provider body")]
        response = self.post()
        self.assertEqual(response.status_code, 503)
        self.assertNotIn("private", response.text)

    def test_rate_limit_blocks_remote_calls(self):
        for _ in range(6):
            FakeProvider.responses = [SAFE, ANSWER, SAFE]
            self.assertEqual(self.post().status_code, 200)
        count = len(FakeProvider.calls)
        self.assertEqual(self.post().status_code, 429)
        self.assertEqual(len(FakeProvider.calls), count)


if __name__ == "__main__":
    unittest.main()
