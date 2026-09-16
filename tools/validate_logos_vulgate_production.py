#!/usr/bin/env python3
"""Validate the pinned production Clementine Vulgate corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "lat_clementine_vulgate"
EXPECTED_COMMIT = "38292f3f91e874d3db9e7e9bf7abd23da3217054"
EXPECTED_BLOB = "a9ec3099e8f641d601679242354366aff150070e"


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise SystemExit(f"Vulgate validation failed: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.exists(): fail("manifest missing")
    manifest = load(manifest_path)
    if manifest.get("corpus_id") != "lat_clementine_vulgate": fail("wrong corpus id")
    if manifest.get("production_enabled") is not True: fail("production disabled")
    if int(manifest.get("book_count") or 0) != 73: fail("expected 73 books")
    if int(manifest.get("chapter_count") or 0) < 1300: fail("unexpectedly low chapter count")
    if int(manifest.get("verse_count") or 0) < 34000: fail("unexpectedly low verse count")

    source = manifest.get("source") or {}
    if source.get("repository") != "jrichter/ClementineVulgateConverter": fail("source repository changed")
    if source.get("commit") != EXPECTED_COMMIT: fail("source commit changed")
    if source.get("git_blob_sha1") != EXPECTED_BLOB: fail("source blob changed")
    if source.get("rights") != "Public Domain": fail("text rights changed")
    if source.get("text_rights_separate_from_mirror_code") is not True: fail("text/code rights boundary missing")

    layers = manifest.get("derived_layers") or {}
    if any(layers.get(k) is not False for k in ("glosses","lemmata","morphology","transliteration")):
        fail("unapproved Latin derived layer enabled")
    vers = manifest.get("versification") or {}
    if vers.get("runtime_exact_identity_required") is not True or vers.get("automatic_remapping") is not False:
        fail("Vulgate versification safety contract changed")

    books_root = root / "books"
    files = sorted(books_root.glob("*.json"))
    if len(files) != 73: fail(f"expected 73 book files, got {len(files)}")
    counted_chapters = 0
    counted_verses = 0
    ids = set()
    for path in files:
        payload = load(path)
        book_id = str(payload.get("book_id") or "")
        if not book_id or book_id in ids: fail("duplicate or empty book id")
        ids.add(book_id)
        if payload.get("production_enabled") is not True: fail(f"{book_id}: production disabled")
        chapters = payload.get("chapters") or {}
        if not chapters: fail(f"{book_id}: no chapters")
        counted_chapters += len(chapters)
        for chapter, verses in chapters.items():
            if not str(chapter).isdigit() or not verses: fail(f"{book_id}: invalid chapter")
            for verse, text in verses.items():
                if not str(verse).isdigit(): fail(f"{book_id} {chapter}: nonnumeric verse")
                if not str(text or "").strip(): fail(f"{book_id} {chapter}:{verse}: empty Latin text")
                counted_verses += 1
    if counted_chapters != int(manifest["chapter_count"]): fail("chapter total mismatch")
    if counted_verses != int(manifest["verse_count"]): fail("verse total mismatch")

    gen = load(books_root / "GEN.json")
    jhn = load(books_root / "JHN.json")
    if not (((gen.get("chapters") or {}).get("1") or {}).get("1")): fail("Genesis 1:1 missing")
    if not (((jhn.get("chapters") or {}).get("1") or {}).get("1")): fail("John 1:1 missing")
    for required in ("TOB","JDT","WIS","SIR","1MA","2MA","BAR","DAN"):
        if required not in ids: fail(f"Catholic book {required} missing")

    print(
        f"Validated Clementine Vulgate production: {manifest['book_count']} books, "
        f"{manifest['chapter_count']} chapters, {manifest['verse_count']} Latin verse records"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
