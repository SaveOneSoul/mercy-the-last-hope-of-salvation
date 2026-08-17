from types import SimpleNamespace

import pytest

from app import recaptcha_service


def _settings(**overrides):
    values = {
        "recaptcha_enforce": True,
        "recaptcha_project_id": "mercy-last-hope-rk-260817",
        "recaptcha_site_key": "test-site-key",
        "recaptcha_min_score": 0.5,
        "recaptcha_allowed_hostnames": ["saveonesoul.github.io"],
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def _request():
    return SimpleNamespace(
        headers={
            "user-agent": "pytest",
            "x-forwarded-for": "203.0.113.10",
        },
        client=SimpleNamespace(host="127.0.0.1"),
    )


def _response(
    *,
    valid=True,
    action="chat",
    hostname="saveonesoul.github.io",
    score=0.9,
):
    return SimpleNamespace(
        token_properties=SimpleNamespace(
            valid=valid,
            action=action,
            hostname=hostname,
        ),
        risk_analysis=SimpleNamespace(
            score=score,
        ),
    )


class FakeClient:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error

    def create_assessment(self, request, timeout):
        if self.error:
            raise self.error
        return self.response


def _install_fake_client(monkeypatch, response=None, error=None):
    monkeypatch.setattr(
        recaptcha_service.recaptchaenterprise_v1,
        "RecaptchaEnterpriseServiceClient",
        lambda: FakeClient(response=response, error=error),
    )


def test_recaptcha_bypasses_when_not_enforced(monkeypatch):
    monkeypatch.setattr(
        recaptcha_service,
        "settings",
        _settings(recaptcha_enforce=False),
    )

    assert (
        recaptcha_service.verify_recaptcha(
            None,
            "chat",
            _request(),
        )
        is None
    )


def test_recaptcha_rejects_missing_token(monkeypatch):
    monkeypatch.setattr(
        recaptcha_service,
        "settings",
        _settings(),
    )

    with pytest.raises(recaptcha_service.RecaptchaRejected):
        recaptcha_service.verify_recaptcha(
            None,
            "chat",
            _request(),
        )


def test_recaptcha_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(
        recaptcha_service,
        "settings",
        _settings(),
    )
    _install_fake_client(
        monkeypatch,
        response=_response(valid=False),
    )

    with pytest.raises(recaptcha_service.RecaptchaRejected):
        recaptcha_service.verify_recaptcha(
            "token",
            "chat",
            _request(),
        )


def test_recaptcha_rejects_wrong_action(monkeypatch):
    monkeypatch.setattr(
        recaptcha_service,
        "settings",
        _settings(),
    )
    _install_fake_client(
        monkeypatch,
        response=_response(action="contact"),
    )

    with pytest.raises(recaptcha_service.RecaptchaRejected):
        recaptcha_service.verify_recaptcha(
            "token",
            "chat",
            _request(),
        )


def test_recaptcha_rejects_wrong_hostname(monkeypatch):
    monkeypatch.setattr(
        recaptcha_service,
        "settings",
        _settings(),
    )
    _install_fake_client(
        monkeypatch,
        response=_response(hostname="attacker.example"),
    )

    with pytest.raises(recaptcha_service.RecaptchaRejected):
        recaptcha_service.verify_recaptcha(
            "token",
            "chat",
            _request(),
        )


def test_recaptcha_rejects_low_score(monkeypatch):
    monkeypatch.setattr(
        recaptcha_service,
        "settings",
        _settings(recaptcha_min_score=0.5),
    )
    _install_fake_client(
        monkeypatch,
        response=_response(score=0.2),
    )

    with pytest.raises(recaptcha_service.RecaptchaRejected):
        recaptcha_service.verify_recaptcha(
            "token",
            "chat",
            _request(),
        )


def test_recaptcha_fails_closed_when_google_unavailable(monkeypatch):
    monkeypatch.setattr(
        recaptcha_service,
        "settings",
        _settings(),
    )
    _install_fake_client(
        monkeypatch,
        error=RuntimeError("provider unavailable"),
    )

    with pytest.raises(recaptcha_service.RecaptchaUnavailable):
        recaptcha_service.verify_recaptcha(
            "token",
            "chat",
            _request(),
        )


def test_recaptcha_accepts_valid_assessment(monkeypatch):
    monkeypatch.setattr(
        recaptcha_service,
        "settings",
        _settings(),
    )
    _install_fake_client(
        monkeypatch,
        response=_response(
            valid=True,
            action="chat",
            hostname="saveonesoul.github.io",
            score=0.9,
        ),
    )

    verdict = recaptcha_service.verify_recaptcha(
        "token",
        "chat",
        _request(),
    )

    assert verdict is not None
    assert verdict.action == "chat"
    assert verdict.hostname == "saveonesoul.github.io"
    assert verdict.score == pytest.approx(0.9)
