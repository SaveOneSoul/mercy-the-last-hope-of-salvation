"""Private AI Ministry policy; no publicly accessible routes are registered.

Session identity and role claims MUST be resolved from the server's signed
authentication session, never from request JSON, user-controlled headers or phone.
"""
from dataclasses import dataclass

MINISTRY_MODULES = (
    "homily", "bible_study", "retreat", "catechesis", "rcia",
    "lesson_planner", "prayer_service", "liturgy", "drafts", "publish",
)


@dataclass(frozen=True)
class MinistryIdentity:
    subject: str
    authenticated: bool
    channel: str
    domains: frozenset[str]
    roles: frozenset[str]
    permissions: frozenset[str]


def can_access_ministry(identity: MinistryIdentity | None, action: str = "read") -> bool:
    if identity is None or not identity.authenticated or not identity.subject:
        return False
    if identity.channel != "web" or "catholic" not in identity.domains:
        return False
    if "owner" in identity.roles:
        return True
    return f"ministry:{action}" in identity.permissions


def private_menu(identity: MinistryIdentity | None) -> list[str]:
    return list(MINISTRY_MODULES) if can_access_ministry(identity) else []
