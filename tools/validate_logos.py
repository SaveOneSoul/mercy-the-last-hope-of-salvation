#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "cloud-backend" / "app" / "logos_seed.json"


def fail(message: str) -> None:
    raise SystemExit(f"Logos validation failed: {message}")


def main() -> int:
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    books = payload.get("books") or []
    if len(books) != 73:
        fail(f"Catholic canon must contain 73 books; found {len(books)}")
    names = [str(row.get("name") or "").strip() for row in books]
    if len(set(names)) != len(names) or any(not name for name in names):
        fail("book names must be non-empty and unique")

    sources = payload.get("sources") or []
    source_ids = {str(row.get("id") or "") for row in sources}
    if "" in source_ids or len(source_ids) != len(sources):
        fail("source ids must be non-empty and unique")
    for source in sources:
        for field in ("title", "status", "rights", "allowed_display_scope"):
            if not str(source.get(field) or "").strip():
                fail(f"source {source.get('id')} is missing {field}")

    passages = payload.get("passages") or {}
    if not passages:
        fail("at least one deterministic seed passage is required")
    for key, passage in passages.items():
        if key != key.lower():
            fail(f"passage key must be normalized lowercase: {key}")
        languages = passage.get("languages") or {}
        for required in ("en", "he", "la", "arc", "grc"):
            if required not in languages:
                fail(f"{passage.get('reference')} is missing the {required} language lane")
        for code, row in languages.items():
            source_id = row.get("source_id")
            if source_id and source_id not in source_ids:
                fail(f"{passage.get('reference')} {code} references unknown source {source_id}")
            if row.get("text") and row.get("status") == "pending":
                fail(f"pending source text must not be rendered: {passage.get('reference')} {code}")
        tokens = (passage.get("interlinear") or {}).get("tokens") or []
        for token in tokens:
            for field in ("surface", "lemma", "morphology", "gloss"):
                if not str(token.get(field) or "").strip():
                    fail(f"interlinear token in {passage.get('reference')} missing {field}")

    for item in payload.get("media") or []:
        for field in ("title", "image_url", "source_url", "rights", "credit"):
            if not str(item.get(field) or "").strip():
                fail(f"media {item.get('id')} is missing {field}")
        if not str(item.get("image_url")).startswith("https://"):
            fail(f"media {item.get('id')} must use HTTPS")

    themes = payload.get("ai_themes") or []
    theme_ids = [str(row.get("id") or "") for row in themes]
    if len(theme_ids) < 10 or len(set(theme_ids)) != len(theme_ids):
        fail("AI theme catalog is missing or contains duplicate ids")

    print(
        f"Logos validation passed: {len(books)} books, {len(sources)} source records, "
        f"{len(passages)} seed passages, {len(payload.get('places') or [])} places, "
        f"{len(payload.get('media') or [])} media records, {len(themes)} AI themes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
