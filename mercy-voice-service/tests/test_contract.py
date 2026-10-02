import base64
import os

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_is_explicit_about_khasi_gate():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["service"] == "mercy-voice"
    assert body["khasi_status"] == "corpus_evaluation_required"


def test_synthesis_requires_auth_by_default(monkeypatch):
    monkeypatch.delenv("MERCY_VOICE_AUTH_MODE", raising=False)
    monkeypatch.delenv("MERCY_VOICE_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("MERCY_VOICE_ALLOW_UNAUTHENTICATED", raising=False)
    response = client.post("/v1/synthesize", json={"text": "Peace.", "language": "en"})
    assert response.status_code == 401


def test_contract_mode_fails_closed_without_test_audio(monkeypatch):
    monkeypatch.setenv("MERCY_VOICE_AUTH_MODE", "token")
    monkeypatch.setenv("MERCY_VOICE_SERVICE_TOKEN", "test-only-token")
    monkeypatch.delenv("MERCY_VOICE_ENABLE_CONTRACT_AUDIO", raising=False)
    response = client.post(
        "/v1/synthesize",
        headers={"Authorization": "Bearer test-only-token"},
        json={"text": "Peace.", "language": "en"},
    )
    assert response.status_code == 503
    assert response.json()["detail"] == "tts_engine_not_configured"


def test_contract_audio_is_labeled_non_speech(monkeypatch):
    monkeypatch.setenv("MERCY_VOICE_AUTH_MODE", "token")
    monkeypatch.setenv("MERCY_VOICE_SERVICE_TOKEN", "test-only-token")
    monkeypatch.setenv("MERCY_VOICE_ENABLE_CONTRACT_AUDIO", "true")
    response = client.post(
        "/v1/synthesize",
        headers={"Authorization": "Bearer test-only-token"},
        json={"text": "Peace.", "language": "kha"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["synthetic_test_audio"] is True
    assert body["engine"] == "contract_only"
    assert body["mime_type"] == "audio/wav"
    assert base64.b64decode(body["audio_base64"], validate=True).startswith(b"RIFF")


def test_kokoro_rejects_khasi_before_engine_call(monkeypatch):
    monkeypatch.setenv("MERCY_VOICE_AUTH_MODE", "token")
    monkeypatch.setenv("MERCY_VOICE_SERVICE_TOKEN", "test-only-token")
    monkeypatch.setenv("MERCY_VOICE_ENGINE", "kokoro")
    response = client.post(
        "/v1/synthesize",
        headers={"Authorization": "Bearer test-only-token"},
        json={"text": "Khublei.", "language": "kha"},
    )
    assert response.status_code == 422
    assert response.json()["detail"] == "language_not_supported_by_engine"


def test_cloud_run_iam_mode_relies_on_platform_auth(monkeypatch):
    monkeypatch.setenv("MERCY_VOICE_AUTH_MODE", "cloud_run_iam")
    monkeypatch.setenv("MERCY_VOICE_ENGINE", "contract_only")
    monkeypatch.delenv("MERCY_VOICE_SERVICE_TOKEN", raising=False)
    monkeypatch.delenv("MERCY_VOICE_ENABLE_CONTRACT_AUDIO", raising=False)
    response = client.post("/v1/synthesize", json={"text": "Peace.", "language": "en"})
    assert response.status_code == 503
    assert response.json()["detail"] == "tts_engine_not_configured"
