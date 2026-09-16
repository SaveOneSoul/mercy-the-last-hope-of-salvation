#!/usr/bin/env python3
"""Vendor the full protocanonical Swete Greek OT layer from the pinned First1KGreek tree.

The existing OT Greek production package remains authoritative for the seven
Catholic deuterocanonical books and the Greek additions. This package adds the
39 protocanonical Old Testament books, using Theodotion for the Daniel base
witness. Source verse boundaries are preserved; Catholic/Douay alignment is
validated at runtime and is never manufactured.
"""
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
DEFAULT_OUTPUT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_ot_swete_full"
REPOSITORY = "OpenGreekAndLatin/First1KGreek"
COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
TREE_ROOT = "data/tlg0527"
TREE_SHA = "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79"
LICENSE_TARGET = "https://creativecommons.org/licenses/by-sa/4.0/"
CORPUS_VERSION = "2026.09.16-swete-protocanonical-39"
ISOLATED_ROOT = "sharealike/first1kgreek_swete_cc-by-sa-4.0"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
WHITESPACE = re.compile(r"\s+")
EXCLUDED_SURFACE_TAGS = {"note", "pb", "milestone", "head"}

WORKS = [
    ("GEN", "Genesis", "tlg001", "Genesis"),
    ("EXO", "Exodus", "tlg002", "Exodus"),
    ("LEV", "Leviticus", "tlg003", "Leviticus"),
    ("NUM", "Numbers", "tlg004", "Numeri"),
    ("DEU", "Deuteronomy", "tlg005", "Deuteronomium"),
    ("JOS", "Joshua", "tlg006", "Josue"),
    ("JDG", "Judges", "tlg008", "Judices"),
    ("RUT", "Ruth", "tlg010", "Ruth"),
    ("1SA", "1 Samuel", "tlg011", "Regnorum I"),
    ("2SA", "2 Samuel", "tlg012", "Regnorum II"),
    ("1KI", "1 Kings", "tlg013", "Regnorum III"),
    ("2KI", "2 Kings", "tlg014", "Regnorum IV"),
    ("1CH", "1 Chronicles", "tlg015", "Paralipomenon I"),
    ("2CH", "2 Chronicles", "tlg016", "Paralipomenon II"),
    ("EZR", "Ezra", "tlg018", "Esdras B"),
    ("NEH", "Nehemiah", "tlg018", "Esdras B"),
    ("EST", "Esther", "tlg019", "Esther"),
    ("JOB", "Job", "tlg032", "Job"),
    ("PSA", "Psalms", "tlg027", "Psalmi"),
    ("PRO", "Proverbs", "tlg029", "Proverbia"),
    ("ECC", "Ecclesiastes", "tlg030", "Ecclesiastes"),
    ("SNG", "Song of Songs", "tlg031", "Canticum"),
    ("ISA", "Isaiah", "tlg048", "Isaias"),
    ("JER", "Jeremiah", "tlg049", "Jeremias"),
    ("LAM", "Lamentations", "tlg051", "Threni seu Lamentationes"),
    ("EZK", "Ezekiel", "tlg053", "Ezechiel"),
    ("DAN", "Daniel", "tlg057", "Daniel (Theodotionis versio)"),
    ("HOS", "Hosea", "tlg036", "Osee"),
    ("JOL", "Joel", "tlg039", "Joel"),
    ("AMO", "Amos", "tlg037", "Amos"),
    ("OBA", "Obadiah", "tlg040", "Abdias"),
    ("JON", "Jonah", "tlg041", "Jonas"),
    ("MIC", "Micah", "tlg038", "Michaeas"),
    ("NAM", "Nahum", "tlg042", "Nahum"),
    ("HAB", "Habakkuk", "tlg043", "Habacuc"),
    ("ZEP", "Zephaniah", "tlg044", "Sophonias"),
    ("HAG", "Haggai", "tlg045", "Aggaeus"),
    ("ZEC", "Zechariah", "tlg046", "Zacharias"),
    ("MAL", "Malachi", "tlg047", "Malachias"),
]


class BuildError(RuntimeError):
    pass


def request_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Mercy-Logos-LXX-Full/1.0"})
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


def fetch_tree() -> dict[str, str]:
    raw = request_bytes(f"https://api.github.com/repos/{REPOSITORY}/git/trees/{TREE_SHA}?recursive=1")
    data = json.loads(raw.decode("utf-8"))
    if data.get("sha") != TREE_SHA or data.get("truncated"):
        raise BuildError("pinned First1KGreek Septuagint tree identity/truncation failure")
    return {
        str(row["path"]): str(row["sha"])
        for row in (data.get("tree") or [])
        if row.get("type") == "blob" and HEX40.fullmatch(str(row.get("sha") or ""))
    }


def download_relative(path: str, inventory: dict[str, str]) -> tuple[bytes, str, str]:
    expected_blob = inventory.get(path)
    if not expected_blob:
        raise BuildError(f"pinned tree does not contain {path}")
    full_path = f"{TREE_ROOT}/{path}"
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/{quote(full_path, safe='/')}"
    payload = request_bytes(url)
    actual_blob = git_blob_sha1(payload)
    if actual_blob != expected_blob:
        raise BuildError(f"Git blob mismatch for {full_path}: expected {expected_blob}, got {actual_blob}")
    return payload, expected_blob, hashlib.sha256(payload).hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def metadata(payload: bytes, work: str) -> tuple[str, str]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise BuildError(f"{work}: invalid CTS metadata XML: {exc}") from exc
    title = next((" ".join("".join(node.itertext()).split()) for node in root.iter() if local_name(node.tag) == "title"), "")
    editions = [str(node.attrib.get("urn") or "") for node in root.iter() if local_name(node.tag) == "edition"]
    candidates = [urn for urn in editions if urn.endswith("1st1K-grc1")]
    if len(candidates) != 1:
        raise BuildError(f"{work}: expected one 1st1K-grc1 CTS edition, found {candidates}")
    return title, candidates[0]


def verify_license(root: ET.Element, book_id: str) -> None:
    for node in root.iter():
        if local_name(node.tag) not in {"licence", "license"}:
            continue
        text = " ".join("".join(node.itertext()).split())
        if node.attrib.get("target") == LICENSE_TARGET and "Attribution-ShareAlike 4.0" in text:
            return
    raise BuildError(f"{book_id}: per-file CC BY-SA 4.0 licence declaration missing")


def surface_text(node: ET.Element) -> str:
    pieces: list[str] = []
    def walk(current: ET.Element) -> None:
        if current.text:
            pieces.append(current.text)
        for child in list(current):
            if local_name(child.tag) not in EXCLUDED_SURFACE_TAGS:
                walk(child)
            if child.tail:
                pieces.append(child.tail)
    walk(node)
    return WHITESPACE.sub(" ", "".join(pieces)).strip()


def parse_tei(payload: bytes, edition_urn: str, book_id: str) -> list[dict]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise BuildError(f"{book_id}: invalid TEI XML: {exc}") from exc
    verify_license(root, book_id)
    edition_nodes = [
        node for node in root.iter()
        if local_name(node.tag) == "div" and node.attrib.get("type") == "edition" and node.attrib.get("n") == edition_urn
    ]
    if len(edition_nodes) != 1:
        raise BuildError(f"{book_id}: selected CTS edition div not found exactly once")
    verses: list[dict] = []
    seen: set[tuple[str | None, str]] = set()

    def walk(node: ET.Element, chapter: str | None = None) -> None:
        if local_name(node.tag) == "div" and node.attrib.get("subtype") == "chapter":
            chapter = str(node.attrib.get("n") or "")
            if not chapter:
                raise BuildError(f"{book_id}: chapter without source n")
        if local_name(node.tag) == "div" and node.attrib.get("subtype") == "verse":
            verse = str(node.attrib.get("n") or "")
            if not verse:
                raise BuildError(f"{book_id}: verse without source n")
            key = (chapter, verse)
            if key in seen:
                raise BuildError(f"{book_id}: duplicate source locus {chapter}:{verse}")
            seen.add(key)
            text = surface_text(node)
            if not text:
                raise BuildError(f"{book_id}: empty source surface at {chapter}:{verse}")
            verses.append({
                "source_chapter": chapter,
                "source_verse": verse,
                "source_reference": f"{chapter}:{verse}" if chapter is not None else verse,
                "surface": text,
            })
            return
        for child in list(node):
            walk(child, chapter)
    walk(edition_nodes[0])
    if not verses:
        raise BuildError(f"{book_id}: no verse divisions parsed")
    return verses


def split_scope(book_id: str, verses: list[dict]) -> tuple[list[dict], dict]:
    if book_id == "EZR":
        selected = [row for row in verses if str(row.get("source_chapter") or "").isdigit() and 1 <= int(row["source_chapter"]) <= 10]
        return selected, {"mode": "esdras-b-component", "source_chapter_start": 1, "source_chapter_end": 10, "canonical_chapter_offset": 0}
    if book_id == "NEH":
        selected = [row for row in verses if str(row.get("source_chapter") or "").isdigit() and 11 <= int(row["source_chapter"]) <= 23]
        return selected, {"mode": "esdras-b-component", "source_chapter_start": 11, "source_chapter_end": 23, "canonical_chapter_offset": 10}
    return verses, {"mode": "source-reference-preserved", "canonical_chapter_offset": 0}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(output: Path) -> dict:
    if len(WORKS) != 39 or len({row[0] for row in WORKS}) != 39:
        raise BuildError("protocanonical Greek work contract must contain exactly 39 Catholic book scopes")
    inventory = fetch_tree()
    if output.exists():
        shutil.rmtree(output)
    books_dir = output / ISOLATED_ROOT / "books"
    books_dir.mkdir(parents=True, exist_ok=True)

    cache: dict[str, tuple[list[dict], dict]] = {}
    stats: list[dict] = []
    total_verses = 0
    for book_id, canonical_name, work, expected_title in WORKS:
        if work not in cache:
            metadata_path = f"{work}/__cts__.xml"
            metadata_bytes, metadata_blob, metadata_sha256 = download_relative(metadata_path, inventory)
            title, edition_urn = metadata(metadata_bytes, work)
            if expected_title.lower() not in title.lower():
                raise BuildError(f"{book_id}: CTS title mismatch: expected {expected_title!r}, got {title!r}")
            text_path = f"{work}/tlg0527.{work}.1st1K-grc1.xml"
            text_bytes, text_blob, text_sha256 = download_relative(text_path, inventory)
            source_verses = parse_tei(text_bytes, edition_urn, book_id)
            cache[work] = (source_verses, {
                "work": work,
                "work_title": title,
                "edition_urn": edition_urn,
                "metadata_path": f"{TREE_ROOT}/{metadata_path}",
                "metadata_git_blob_sha1": metadata_blob,
                "metadata_sha256": metadata_sha256,
                "text_path": f"{TREE_ROOT}/{text_path}",
                "text_git_blob_sha1": text_blob,
                "text_sha256": text_sha256,
            })
        source_verses, source_meta = cache[work]
        verses, mapping = split_scope(book_id, source_verses)
        if not verses:
            raise BuildError(f"{book_id}: source split produced no verses")
        payload = {
            "schema_version": 1,
            "corpus_id": "grc_ot_swete_full",
            "corpus_version": CORPUS_VERSION,
            "production_enabled": True,
            "partition": "sharealike-first1kgreek-swete",
            "license": "CC BY-SA 4.0",
            "share_alike": True,
            "isolation_required": True,
            "book_id": book_id,
            "book": canonical_name,
            "language": "grc",
            "mapping": mapping,
            "source": {
                "repository": REPOSITORY,
                "commit": COMMIT,
                **source_meta,
                "per_file_license_verified": True,
            },
            "surface_policy": {
                "source_boundaries_preserved": True,
                "unicode_normalization": "none",
                "whitespace": "collapsed-layout-whitespace",
                "excluded_editorial_tags": sorted(EXCLUDED_SURFACE_TAGS),
                "glosses": False,
                "lemmata": False,
                "morphology": False,
                "transliteration": False,
            },
            "verses": verses,
        }
        write_json(books_dir / f"{book_id}.json", payload)
        chapter_values = {str(v.get("source_chapter")) for v in verses if v.get("source_chapter") is not None}
        stats.append({
            "book_id": book_id,
            "book": canonical_name,
            "work": work,
            "work_title": source_meta["work_title"],
            "edition_urn": source_meta["edition_urn"],
            "chapter_count": len(chapter_values),
            "verse_count": len(verses),
            "mapping": mapping,
            "text_git_blob_sha1": source_meta["text_git_blob_sha1"],
            "text_sha256": source_meta["text_sha256"],
        })
        total_verses += len(verses)

    manifest = {
        "schema_version": 1,
        "corpus_id": "grc_ot_swete_full",
        "corpus_version": CORPUS_VERSION,
        "status": "production-installed",
        "production_enabled": True,
        "language": "grc",
        "scope": "39 protocanonical Catholic Old Testament book scopes from Swete; complements the accepted deuterocanonical/additions production package",
        "book_count": 39,
        "verse_record_count": total_verses,
        "books": stats,
        "source": {
            "repository": REPOSITORY,
            "commit": COMMIT,
            "septuagint_path": TREE_ROOT,
            "septuagint_tree_sha": TREE_SHA,
            "license": "CC BY-SA 4.0",
            "license_target": LICENSE_TARGET,
            "share_alike": True,
            "isolation_required": True,
            "attribution": "OpenGreekAndLatin First1KGreek / Henry Barclay Swete Septuagint witnesses.",
        },
        "partition": {"path": ISOLATED_ROOT, "license": "CC BY-SA 4.0", "share_alike": True, "isolation_required": True},
        "runtime_contract": {
            "local_only": True,
            "source_boundaries_preserved": True,
            "automatic_versification_remapping": False,
            "exact_douay_rheims_alignment_required_before_parallel_render": True,
            "deuterocanonical_package": "grc_ot_catholic_swete",
            "daniel_primary_base_witness": "Theodotion",
            "ezra_nehemiah_source": "Esdras B",
        },
        "derived_layers": {"glosses": False, "lemmata": False, "morphology": False, "transliteration": False},
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = build(args.output.resolve())
    print(f"[OT Greek Full] vendored {manifest['book_count']} protocanonical book scopes / {manifest['verse_record_count']} source verse records")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        raise SystemExit(f"OT Greek full build failed: {exc}") from exc
