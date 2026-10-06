"""Shared AI Core contract v1, implemented locally to preserve deployment isolation.

Providers implement generate(prompt, domain, context). Domain-specific validators
approve the result; no unvalidated completion is returned. No network calls here.
"""
from dataclasses import dataclass
from typing import Any, Callable, Mapping

AI_CORE_CONTRACT_VERSION = "1.0"
AI_DOMAINS = frozenset({"catholic", "insurance"})


class AICoreError(Exception):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class AIIdentity:
    subject: str
    authenticated: bool
    domains: frozenset[str]
    permissions: frozenset[str]


def authorize_ai_request(identity: AIIdentity, domain: str, permission: str) -> None:
    if domain not in AI_DOMAINS:
        raise AICoreError("unknown_domain")
    if not identity or not identity.authenticated or not identity.subject:
        raise AICoreError("authentication_required")
    if domain not in identity.domains:
        raise AICoreError("domain_forbidden")
    if permission not in identity.permissions and f"{domain}:*" not in identity.permissions:
        raise AICoreError("permission_denied")


class SharedAICore:
    def __init__(
        self,
        providers: Mapping[str, Any],
        validator: Callable[..., dict],
        audit: Callable[[dict], None] | None = None,
    ):
        self.providers = providers
        self.validator = validator
        self.audit = audit or (lambda event: None)

    def execute(self, *, identity: AIIdentity, domain: str, permission: str,
                prompt: str, provider: str, context: dict | None = None) -> dict:
        authorize_ai_request(identity, domain, permission)
        if not isinstance(prompt, str) or not prompt.strip():
            raise AICoreError("invalid_prompt")
        adapter = self.providers.get(provider)
        if adapter is None or not callable(getattr(adapter, "generate", None)):
            raise AICoreError("provider_unavailable")
        try:
            result = adapter.generate(prompt=prompt.strip(), domain=domain, context=context or {})
            approved = self.validator(domain=domain, result=result, context=context or {})
            if not isinstance(approved, dict) or approved.get("approved") is not True:
                raise AICoreError("validation_failed")
            text = approved.get("text")
            if not isinstance(text, str) or not text.strip():
                raise AICoreError("validation_failed")
            output = {
                "text": text,
                "sources": approved.get("sources", []),
                "provider": provider,
                "contract": AI_CORE_CONTRACT_VERSION,
            }
            self.audit({"domain": domain, "subject": identity.subject, "provider": provider, "status": "success"})
            return output
        except Exception as exc:
            self.audit({"domain": domain, "subject": identity.subject, "provider": provider,
                        "status": "failed", "code": getattr(exc, "code", "provider_error")})
            raise
