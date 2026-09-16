#!/usr/bin/env python3
"""Vendor the pinned public-domain Clementine Vulgate into Logos JSON corpus files."""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
BOOKS_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "books.json"
DEFAULT_OUTPUT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "lat_vulgate_clementine"
REPOSITORY = "seven1m/open-bibles"
COMMIT = "f257a3559025c3f873b48a75019f53a9354ed7de"
SOURCE_PATH = "lat-clementine.usfx.xml"
SOURCE_GIT_BLOB_SHA1 = "c0e65106383658fd914e90da4c82f2be48a0a762"
README_GIT_BLOB_SHA1 = "50caf5d5b86fb69471c1b849584cc476a7944df5"
CORPUS_VERSION = "2026.09.16-clementine-open-bibles"
WHITESPACE = re.compile(r"\s+")


class BuildError(RuntimeError):
    pass


def request_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Mercy-Logos-Vulgate/1.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=90) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise BuildError(f"failed to download {url}: {last_error}")


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def download_pinned(path: str, expected_blob: str) -> tuple[bytes, str]:
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/{path}"
    payload = request_bytes(url)
    actual = git_blob_sha1(payload)
    if actual != expected_blob:
        raise BuildError(f"Git blob mismatch for {path}: expected {expected_blob}, got {actual}")
    return payload, hashlib.sha256(payload).hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def clean(text: str) -> str:
    return WHITESPACE.sub(" ", text).strip()


def books_contract() -> list[dict]:
    try:
        payload = json.loads(BOOKS_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read Catholic canon contract: {exc}") from exc
    rows = payload.get("books") or []
    if len(rows) != 73:
        raise BuildError(f"Catholic canon contract changed: expected 73 books, got {len(rows)}")
    return rows


def parse_usfx(payload: bytes) -> dict[str, dict]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise BuildError(f"invalid Clementine USFX XML: {exc}") from exc
    if local_name(root.tag).lower() != "usfx":
        raise BuildError("unexpected Clementine root element")

    parsed: dict[str, dict] = {}
    for book in [node for node in list(root) if local_name(node.tag) == "book"]:
        source_id = str(book.attrib.get("id") or "").upper()
        if not source_id:
            raise BuildError("Clementine book without id")
        if source_id in parsed:
            raise BuildError(f"duplicate Clementine book id {source_id}")
        title = ""
        chapter: str | None = None
        verse: str | None = None
        pieces: list[str] = []
        chapters: dict[str, dict[str, str]] = {}

        def finish_verse() -> None:
            nonlocal verse, pieces
            if verse is None:
                return
            if chapter is None:
                raise BuildError(f"{source_id}: verse {verse} appeared before a chapter")
            text = clean("".join(pieces))
            if not text:
                raise BuildError(f"{source_id} {chapter}:{verse}: empty Latin verse")
            bucket = chapters.setdefault(chapter, {})
            if verse in bucket:
                raise BuildError(f"{source_id} {chapter}:{verse}: duplicate Latin verse")
            bucket[verse] = text
            verse = None
            pieces = []

        def node_surface(node: ET.Element) -> str:
            chunks: list[str] = []
            if node.text:
                chunks.append(node.text)
            for child in list(node):
                chunks.append(node_surface(child))
                if child.tail:
                    chunks.append(child.tail)
            return "".join(chunks)

        for child in list(book):
            tag = local_name(child.tag)
            if tag == "h" and not title:
                title = clean("".join(child.itertext()))
            elif tag == "c":
                finish_verse()
                chapter = str(child.attrib.get("id") or "")
                if not chapter:
                    raise BuildError(f"{source_id}: chapter without id")
            elif tag == "v":
                finish_verse()
                verse = str(child.attrib.get("id") or "")
                if not verse:
                    raise BuildError(f"{source_id}: verse without id")
                if child.tail:
                    pieces.append(child.tail)
            elif tag == "ve":
                finish_verse()
            elif verse is not None:
                pieces.append(node_surface(child))
                if child.tail:
                    pieces.append(child.tail)
        finish_verse()
        if not chapters:
            raise BuildError(f"{source_id}: no chapters parsed")
        parsed[source_id] = {"title": title or source_id, "chapters": chapters}
    return parsed


def canonical_source_id(book_id: str) -> str:
    return book_id


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(output: Path) -> dict:
    source_bytes, source_sha256 = download_pinned(SOURCE_PATH, SOURCE_GIT_BLOB_SHA1)
    readme_bytes, readme_sha256 = download_pinned("README.md", README_GIT_BLOB_SHA1)
    readme = readme_bytes.decode("utf-8", errors="strict")
    if "lat-clementine.usfx.xml" not in readme or "Clementine Latin Vulgate" not in readme or "Public Domain" not in readme:
        raise BuildError("upstream README no longer proves the Clementine public-domain declaration")

    parsed = parse_usfx(source_bytes)
    canon = books_contract()
    expected_ids = {canonical_source_id(str(row["id"])) for row in canon}
    source_ids = set(parsed)
    missing = sorted(expected_ids - source_ids)
    extras = sorted(source_ids - expected_ids)
    if missing or extras:
        raise BuildError(f"Clementine 73-book inventory mismatch; missing={missing}, extras={extras}")

    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    book_stats: list[dict] = []
    total_chapters = 0
    total_verses = 0
    for row in canon:
        book_id = str(row["id"])
        source_id = canonical_source_id(book_id)
        source = parsed[source_id]
        chapters = source["chapters"]
        chapter_count = len(chapters)
        verse_count = sum(len(v) for v in chapters.values())
        total_chapters += chapter_count
        total_verses += verse_count
        payload = {
            "schema_version": 1,
            "corpus_id": "lat_vulgate_clementine",
            "corpus_version": CORPUS_VERSION,
            "production_enabled": True,
            "language": "la",
            "book_id": book_id,
            "book": row["name"],
            "order": row["order"],
            "source_book_id": source_id,
            "source_title": source["title"],
            "chapters": chapters,
        }
        filename = f"{book_id.lower()}.json"
        write_json(output / filename, payload)
        book_stats.append({
            "id": book_id,
            "name": row["name"],
            "order": row["order"],
            "filename": filename,
            "source_book_id": source_id,
            "source_title": source["title"],
            "chapter_count": chapter_count,
            "verse_count": verse_count,
        })

    manifest = {
        "schema_version": 1,
        "corpus_id": "lat_vulgate_clementine",
        "corpus_version": CORPUS_VERSION,
        "status": "production-installed",
        "production_enabled": True,
        "language": "la",
        "scope": "Complete 73-book Clementine Latin Vulgate",
        "book_count": len(book_stats),
        "chapter_count": total_chapters,
        "verse_count": total_verses,
        "books": book_stats,
        "source": {
            "title": "Clementine Latin Vulgate",
            "repository": REPOSITORY,
            "commit": COMMIT,
            "path": SOURCE_PATH,
            "git_blob_sha1": SOURCE_GIT_BLOB_SHA1,
            "sha256": source_sha256,
            "rights": "public-domain",
            "license": "Public Domain",
            "rights_evidence": {
                "path": "README.md",
                "git_blob_sha1": README_GIT_BLOB_SHA1,
                "sha256": readme_sha256,
            },
            "attribution": "Clementine Latin Vulgate via seven1m/open-bibles public-domain corpus.",
        },
        "runtime_contract": {
            "local_only": True,
            "automatic_versification_remapping": False,
            "exact_douay_rheims_alignment_required_before_parallel_render": True,
        },
        "derived_layers": {"lemma": False, "morphology": False, "gloss": False, "transliteration": False},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = build(args.output.resolve())
    print(f"[Vulgate] vendored {manifest['book_count']} books / {manifest['chapter_count']} chapters / {manifest['verse_count']} verses")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        raise SystemExit(f"Vulgate build failed: {exc}") from exc
