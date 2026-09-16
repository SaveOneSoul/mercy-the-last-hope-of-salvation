#!/usr/bin/env python3
"""Vendor the pinned 73-book public-domain Clementine Latin Vulgate."""

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
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "vulgate" / "source-lock.json"
DRA_MANIFEST = ROOT / "cloud-backend" / "app" / "logos_corpus" / "eng_douay_rheims_1899" / "manifest.json"
DEFAULT_OUTPUT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "lat_clementine_vulgate"
CORPUS_VERSION = "2026.09.16-clementine-vulgate-73"
WHITESPACE = re.compile(r"\s+")


class BuildError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read {path}: {exc}") from exc


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


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


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_usfx(payload: bytes) -> tuple[dict[str, dict], int, int]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise BuildError(f"invalid Clementine USFX XML: {exc}") from exc
    if local_name(root.tag) != "usfx":
        raise BuildError("Clementine source root is not USFX")

    books: dict[str, dict] = {}
    chapter_total = 0
    verse_total = 0
    for book in list(root):
        if local_name(book.tag) != "book":
            continue
        book_id = str(book.attrib.get("id") or "").upper()
        if not book_id or book_id in books:
            raise BuildError(f"invalid or duplicate Vulgate book id: {book_id!r}")
        title = ""
        current_chapter: str | None = None
        chapters: dict[str, dict[str, str]] = {}
        for node in list(book):
            tag = local_name(node.tag)
            if tag == "h":
                title = WHITESPACE.sub(" ", "".join(node.itertext())).strip()
            elif tag == "c":
                current_chapter = str(node.attrib.get("id") or "")
                if not current_chapter.isdigit():
                    raise BuildError(f"{book_id}: nonnumeric chapter id {current_chapter!r}")
                chapters.setdefault(current_chapter, {})
            elif tag == "v":
                if current_chapter is None:
                    raise BuildError(f"{book_id}: verse before chapter")
                verse = str(node.attrib.get("id") or "")
                if not verse.isdigit():
                    raise BuildError(f"{book_id} {current_chapter}: nonnumeric verse id {verse!r}")
                text = WHITESPACE.sub(" ", (node.tail or "")).strip()
                if not text:
                    raise BuildError(f"{book_id} {current_chapter}:{verse}: empty Latin text")
                if verse in chapters[current_chapter]:
                    raise BuildError(f"{book_id} {current_chapter}:{verse}: duplicate verse")
                chapters[current_chapter][verse] = text
        if not chapters:
            raise BuildError(f"{book_id}: no chapters parsed")
        count = sum(len(v) for v in chapters.values())
        chapter_total += len(chapters)
        verse_total += count
        books[book_id] = {
            "book_id": book_id,
            "book": title or book_id,
            "chapter_count": len(chapters),
            "verse_count": count,
            "chapters": chapters,
        }
    return books, chapter_total, verse_total


def build(output: Path) -> dict:
    lock = load_json(LOCK_PATH)
    source = lock.get("source") or {}
    if lock.get("phase") != "Latin Vulgate Production" or lock.get("production_enabled") is not False:
        raise BuildError("unexpected Vulgate source lock")
    if source.get("rights") != "Public Domain":
        raise BuildError("Vulgate source must remain public domain")

    repo = str(source.get("repository") or "")
    commit = str(source.get("commit") or "")
    path = str(source.get("path") or "")
    expected_blob = str(source.get("git_blob_sha1") or "")
    if repo != "jrichter/ClementineVulgateConverter":
        raise BuildError("unexpected Vulgate source repository")
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{quote(path, safe='/')}"
    raw = request_bytes(url)
    actual_blob = git_blob_sha1(raw)
    if actual_blob != expected_blob:
        raise BuildError(f"Vulgate Git blob mismatch: expected {expected_blob}, got {actual_blob}")
    source_sha256 = hashlib.sha256(raw).hexdigest()

    books, chapter_total, verse_total = parse_usfx(raw)
    dra = load_json(DRA_MANIFEST)
    dra_ids = {str(row.get("id")) for row in (dra.get("books") or [])}
    if len(dra_ids) != 73:
        raise BuildError("installed Douay-Rheims canon is not 73 books")
    if set(books) != dra_ids:
        missing = sorted(dra_ids - set(books))
        extra = sorted(set(books) - dra_ids)
        raise BuildError(f"Vulgate/DRA canon mismatch; missing={missing}, extra={extra}")

    target = output.resolve()
    if target == ROOT.resolve():
        raise BuildError("refusing repository root as Vulgate output")
    if target.exists():
        shutil.rmtree(target)
    books_dir = target / "books"
    books_dir.mkdir(parents=True, exist_ok=True)

    stats = []
    for book_id in sorted(books):
        row = books[book_id]
        payload = {
            "schema_version": 1,
            "corpus_id": "lat_clementine_vulgate",
            "corpus_version": CORPUS_VERSION,
            "production_enabled": True,
            "language": "la",
            **row,
            "source": {
                "id": source.get("id"),
                "repository": repo,
                "commit": commit,
                "path": path,
                "git_blob_sha1": expected_blob,
                "sha256": source_sha256,
                "rights": "Public Domain",
                "attribution": source.get("attribution"),
            },
        }
        write_json(books_dir / f"{book_id}.json", payload)
        stats.append({
            "book_id": book_id,
            "book": row["book"],
            "chapter_count": row["chapter_count"],
            "verse_count": row["verse_count"],
        })

    manifest = {
        "schema_version": 1,
        "corpus_id": "lat_clementine_vulgate",
        "corpus_version": CORPUS_VERSION,
        "status": "production-installed",
        "production_enabled": True,
        "language": "la",
        "scope": "Full 73-book Sixto-Clementine Latin Vulgate",
        "book_count": len(stats),
        "chapter_count": chapter_total,
        "verse_count": verse_total,
        "books": stats,
        "supported_canonical_books": sorted(books),
        "source": {
            "id": source.get("id"),
            "title": source.get("title"),
            "edition": source.get("edition"),
            "repository": repo,
            "commit": commit,
            "path": path,
            "git_blob_sha1": expected_blob,
            "sha256": source_sha256,
            "upstream": source.get("upstream"),
            "rights": "Public Domain",
            "attribution": source.get("attribution"),
            "text_rights_separate_from_mirror_code": True,
        },
        "derived_layers": {
            "glosses": False,
            "lemmata": False,
            "morphology": False,
            "transliteration": False,
        },
        "versification": {
            "canonical_reference_system": "Douay-Rheims Catholic 73-book corpus",
            "source_reference_system": "Clementine Vulgate chapter/verse numbering",
            "runtime_exact_identity_required": True,
            "automatic_remapping": False,
            "fabricate_verse_boundaries": False,
            "mismatched_chapters_blocked_until_explicit_mapping": True,
        },
        "serving_contract": {
            "english_corpus_unchanged": True,
            "source_latin_preserved": True,
            "no_english_scripture_text_in_package": True,
            "no_fabricated_linguistic_annotation": True,
        },
    }
    write_json(target / "manifest.json", manifest)
    print(
        f"[Vulgate] packaged {manifest['book_count']} books / {manifest['chapter_count']} chapters / "
        f"{manifest['verse_count']} Latin verse records; public-domain source locked"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        raise SystemExit(f"Vulgate production build failed: {exc}") from exc
