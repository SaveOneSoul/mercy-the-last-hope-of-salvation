from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PREFIXES = ("cloud-backend/", "backend/", ".git/")

FORM_RE = re.compile(r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>", re.I | re.S)
FIELD_RE = re.compile(r"<(?:input|textarea|select)\b[^>]*?name=[\"']([^\"']+)[\"'][^>]*>", re.I | re.S)
BUTTON_RE = re.compile(r"<button\b[^>]*>(.*?)</button>", re.I | re.S)


def public_html_files():
    for path in ROOT.rglob("*.html"):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(EXCLUDED_PREFIXES):
            continue
        yield path, rel


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def describe_form(rel: str, attrs: str, body: str) -> str:
    fields = FIELD_RE.findall(body)
    buttons = [re.sub(r"<[^>]+>", "", b).strip() for b in BUTTON_RE.findall(body)]
    attrs_clean = re.sub(r"\s+", " ", attrs).strip()
    return f"{rel} | attrs=[{attrs_clean}] | fields={fields} | buttons={buttons}"


def has_named_field(body: str, name: str) -> bool:
    body_l = body.lower()
    return f'name="{name}"' in body_l or f"name='{name}'" in body_l


def require_submit_status_script(marker: str, body_l: str, page_l: str, errors: list[str]) -> None:
    require('type="submit"' in body_l or "type='submit'" in body_l, f"{marker} form missing submit button", errors)
    require('role="status"' in body_l or 'class="status"' in body_l or 'data-form-status' in body_l, f"{marker} form missing status output", errors)
    require("public-forms.js" in page_l, f"{marker} form does not load public-forms.js", errors)


def audit_form(rel: str, attrs: str, body: str, page: str, errors: list[str]) -> None:
    marker = f"{rel}:"
    attrs_l = attrs.lower()
    body_l = body.lower()
    page_l = page.lower()

    if "data-prayer-network-form" in attrs_l:
        for field in ("name", "intention", "share_worldwide"):
            require(has_named_field(body, field), f"{marker} prayer-network form missing {field} field", errors)
        require_submit_status_script(marker, body_l, page_l, errors)
        return

    if "data-mass-intention-form" in attrs_l:
        for field in ("requester_name", "requester_email", "intention_for_name", "intention_text", "life_status", "masses_requested", "consent_priest_distribution"):
            require(has_named_field(body, field), f"{marker} Mass-intention form missing {field} field", errors)
        require_submit_status_script(marker, body_l, page_l, errors)
        return

    if "data-priest-registration-form" in attrs_l:
        for field in ("full_name", "email", "country", "diocese_or_institute", "bishop_or_superior", "verification_contact", "declaration_authorized"):
            require(has_named_field(body, field), f"{marker} priest-registration form missing {field} field", errors)
        require_submit_status_script(marker, body_l, page_l, errors)
        return

    if "data-prayer-form" in attrs_l:
        require(has_named_field(body, "intention"), f"{marker} prayer form missing intention field", errors)
        require_submit_status_script(marker, body_l, page_l, errors)
        return

    if "data-contact-form" in attrs_l:
        for field in ("name", "email", "message"):
            require(has_named_field(body, field), f"{marker} contact form missing {field} field", errors)
        require('type="submit"' in body_l or "type='submit'" in body_l, f"{marker} contact form missing submit button", errors)
        require("data-form-status" in body_l or 'class="status"' in body_l or 'class="form-status"' in body_l, f"{marker} contact form missing status output", errors)
        require("public-forms.js" in page_l or "main.js" in page_l, f"{marker} contact form does not load an approved contact handler", errors)
        return

    if "data-catholic-ai-form" in attrs_l:
        require("data-catholic-ai-input" in body_l, f"{marker} Catholic AI form missing input hook", errors)
        require("data-catholic-ai-status" in body_l, f"{marker} Catholic AI form missing status hook", errors)
        require("catholic-ai.js" in page_l, f"{marker} Catholic AI form does not load catholic-ai.js", errors)
        return

    if "data-chat-form" in attrs_l:
        require("data-chat-input" in body_l, f"{marker} Mercy Guide form missing chat input hook", errors)
        require("data-chat-messages" in page_l, f"{marker} Mercy Guide page missing chat message output", errors)
        require("chatbot.js" in page_l, f"{marker} Mercy Guide form does not load chatbot.js", errors)
        return

    errors.append(f"{marker} unrecognized public form has no approved submission handler :: {describe_form(rel, attrs, body)}")


def main() -> int:
    errors: list[str] = []
    found: list[str] = []
    diagnostics: list[str] = []

    for path, rel in public_html_files():
        page = path.read_text(encoding="utf-8")
        for match in FORM_RE.finditer(page):
            found.append(rel)
            diagnostics.append(describe_form(rel, match.group("attrs"), match.group("body")))
            audit_form(rel, match.group("attrs"), match.group("body"), page, errors)

    print("Public forms audited:")
    if found:
        for item in diagnostics:
            print(f" - {item}")
    else:
        print(" - none")

    if errors:
        print("\nFORM AUDIT FAILED")
        for error in errors:
            print(f" - {error}")
        return 1

    print("\nFORM AUDIT PASSED")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
