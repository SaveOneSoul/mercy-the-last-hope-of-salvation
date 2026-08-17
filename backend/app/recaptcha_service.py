from __future__ import annotations

from dataclasses import dataclass

from fastapi import Request
from google.cloud import recaptchaenterprise_v1

from .settings import settings


class RecaptchaRejected(Exception):
    """The request failed reCAPTCHA verification."""


class RecaptchaUnavailable(Exception):
    """The reCAPTCHA service could not be used safely."""


@dataclass(frozen=True)
class RecaptchaVerdict:
    score: float
    hostname: str
    action: str


def _request_ip(request: Request) -> str:
    # Google frontends append forwarding information. Cloud Armor/load-balancer hardening
    # will become the authoritative edge control; this value is only a reCAPTCHA signal.
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else ""


def verify_recaptcha(
    token: str | None,
    expected_action: str,
    request: Request,
) -> RecaptchaVerdict | None:
    if not settings.recaptcha_enforce:
        return None

    if not settings.recaptcha_project_id or not settings.recaptcha_site_key:
        raise RecaptchaUnavailable("reCAPTCHA is enforced but not fully configured.")

    if not token:
        raise RecaptchaRejected("Missing reCAPTCHA token.")

    allowed = {
        h.strip().lower()
        for h in settings.recaptcha_allowed_hostnames
        if h.strip()
    }
    if not allowed:
        raise RecaptchaUnavailable(
            "reCAPTCHA is enforced but allowed hostnames are not configured."
        )

    event = recaptchaenterprise_v1.Event(
        site_key=settings.recaptcha_site_key,
        token=token,
        expected_action=expected_action,
        user_ip_address=_request_ip(request),
        user_agent=request.headers.get("user-agent", "")[:1024],
    )
    assessment = recaptchaenterprise_v1.Assessment(event=event)
    client = recaptchaenterprise_v1.RecaptchaEnterpriseServiceClient()

    try:
        response = client.create_assessment(
            request=recaptchaenterprise_v1.CreateAssessmentRequest(
                parent=f"projects/{settings.recaptcha_project_id}",
                assessment=assessment,
            ),
            timeout=5.0,
        )
    except Exception as exc:
        raise RecaptchaUnavailable("reCAPTCHA assessment failed.") from exc

    props = response.token_properties
    if not props.valid:
        raise RecaptchaRejected("Invalid reCAPTCHA token.")

    if props.action.lower() != expected_action.lower():
        raise RecaptchaRejected("Unexpected reCAPTCHA action.")

    hostname = (props.hostname or "").lower()
    if hostname not in allowed:
        raise RecaptchaRejected("Unexpected reCAPTCHA hostname.")

    score = float(response.risk_analysis.score or 0.0)
    if score < settings.recaptcha_min_score:
        raise RecaptchaRejected("reCAPTCHA score below threshold.")

    return RecaptchaVerdict(
        score=score,
        hostname=hostname,
        action=props.action,
    )
