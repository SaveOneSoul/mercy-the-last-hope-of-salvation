from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PREFIXES = ("cloud-backend/", "backend/", ".git/")

FORM_RE = re.compile(r"<form\b(?P<attrs>[^>]*)>(?P<body>.*?)</form>", re.I | re.S)


def public_html_files():
    for path in ROOT.rglob("*.html"):
        rel = path.relative_to(ROOT).as_posix()
        if rel.startswith(EXCLUDED_PREFIXES):
            continue
        yield path, rel


def require(condition: bool, message: str, errors: list[str]) -> None:
    if not condition:
        errors.append(message)


def audit_form(rel: str, attrs: str, body: str, page: str, errors: list[str]) -> None:
    marker = f"{rel}:"
    attrs_l = attrs.lower()
    body_l = body.lower()

    if "data-prayer-form" in attrs_l:
        require('name="intention"' in body_l, f"{marker} prayer form missing intention field", errors)
        require('type="submit"' in body_l, f"{marker} prayer form missing submit button", errors)
        require('role="status"' in body_l or 'class="status"' in body_l, f"{marker} prayer form missing status output", errors)
        require("public-forms.js" in page, f"{marker} prayer form does not load public-forms.js", errors)
        return

    if "data-contact-form" in attrs_l:
        for field in ("name", "email", "subject", "message"):
            require(f'name="{field}"' in body_l, f"{marker} contact form missing {field} field", errors)
        require('type="submit"' in body_l, f"{marker} contact form missing submit button", errors)
        require("public-forms.js" in page, f"{marker} contact form does not load public-forms.js", errors)
        return

    if "data-catholic-ai-form" in attrs_l:
        require("data-catholic-ai-input" in body_l, f"{marker} Catholic AI form missing input hook", errors)
        require("data-catholic-ai-status" in body_l, f"{marker} Catholic AI form missing status hook", errors)
        require("catholic-ai.js" in page, f"{marker} Catholic AI form does not load catholic-ai.js", errors)
        return

    errors.append(f"{marker} unrecognized public form has no approved submission handler")


def main() -> int:
    errors: list[str] = []
    found: list[str] = []

    for path, rel in public_html_files():
        page = path.read_text(encoding="utf-8")
        for match in FORM_RE.finditer(page):
            found.append(rel)
            audit_form(rel, match.group("attrs"), match.group("body"), page, errors)

    print("Public forms audited:")
    if found:
        for rel in found:
            print(f" - {rel}")
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
