#!/usr/bin/env python3
"""Vendor the complete protocanonical Catholic Greek OT companion corpus.

Thirty-eight book scopes come from the pinned OpenGreekAndLatin First1KGreek
Swete tree. Ecclesiastes is the documented First1K gap: its CTS metadata exists
but the Greek edition blob does not. For Ecclesiastes only, this importer uses a
pinned Open Greek Corpus verse-keyed Greek Wikisource LXX witness under
CC BY-SA 4.0. The fallback is recorded explicitly and is never represented as
Swete.

The accepted grc_ot_catholic_swete package remains authoritative for the seven
Catholic deuterocanonical books and the Greek additions to Esther and Daniel.
Source verse boundaries, including explicitly empty First1K source divisions,
are preserved. No versification remapping or linguistic annotation is fabricated.
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
DEFAULT_OUTPUT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_ot_catholic_full"

FIRST1K_REPOSITORY = "OpenGreekAndLatin/First1KGreek"
FIRST1K_COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
FIRST1K_TREE_ROOT = "data/tlg0527"
FIRST1K_TREE_SHA = "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79"
FIRST1K_LICENSE_TARGET = "https://creativecommons.org/licenses/by-sa/4.0/"

ECC_REPOSITORY = "open-greek/open-greek-corpus"
ECC_COMMIT = "338aa27310b3cfe2588a993b4d113b503597d70f"
ECC_PATH = "data/corpus/septuaginta.ecclesiastes.jsonl"
ECC_GIT_BLOB_SHA1 = "1659770789d318e7ee04f3ee03684bf880922bc4"
ECC_LICENSE_PATH = "LICENSE"
ECC_LICENSE_GIT_BLOB_SHA1 = "8259e21ad92848217dcdfd4067d8a919765eb4a7"
ECC_INGEST_PATH = "scripts/ingest_wikisource_ecclesiastes.py"
ECC_INGEST_GIT_BLOB_SHA1 = "cef0ca6d447741352c1d2c9924b6af46a3de3862"
ECC_LICENSE_STRING = "PD (ancient LXX text); Wikisource transcription CC BY-SA 4.0"

CORPUS_VERSION = "2026.09.17-catholic-lxx-full"
ISOLATED_ROOT = "sharealike/catholic_lxx_cc-by-sa-4.0"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
WHITESPACE = re.compile(r"\s+")
EXCLUDED_SURFACE_TAGS = {"note", "pb", "milestone", "head"}

# Catholic canonical book id -> pinned First1K work id. Ecclesiastes retains its
# First1K work id for identity/provenance, but its surface comes from the pinned
# Wikisource-derived Open Greek Corpus fallback documented above.
WORKS = [
    ("GEN", "Genesis", "tlg001"), ("EXO", "Exodus", "tlg002"),
    ("LEV", "Leviticus", "tlg003"), ("NUM", "Numbers", "tlg004"),
    ("DEU", "Deuteronomy", "tlg005"), ("JOS", "Joshua", "tlg006"),
    ("JDG", "Judges", "tlg008"), ("RUT", "Ruth", "tlg010"),
    ("1SA", "1 Samuel", "tlg011"), ("2SA", "2 Samuel", "tlg012"),
    ("1KI", "1 Kings", "tlg013"), ("2KI", "2 Kings", "tlg014"),
    ("1CH", "1 Chronicles", "tlg015"), ("2CH", "2 Chronicles", "tlg016"),
    ("EZR", "Ezra", "tlg018"), ("NEH", "Nehemiah", "tlg018"),
    ("EST", "Esther", "tlg019"), ("JOB", "Job", "tlg032"),
    ("PSA", "Psalms", "tlg027"), ("PRO", "Proverbs", "tlg029"),
    ("ECC", "Ecclesiastes", "tlg030"), ("SNG", "Song of Songs", "tlg031"),
    ("ISA", "Isaiah", "tlg048"), ("JER", "Jeremiah", "tlg049"),
    ("LAM", "Lamentations", "tlg051"), ("EZK", "Ezekiel", "tlg053"),
    ("DAN", "Daniel", "tlg057"), ("HOS", "Hosea", "tlg036"),
    ("JOL", "Joel", "tlg039"), ("AMO", "Amos", "tlg037"),
    ("OBA", "Obadiah", "tlg040"), ("JON", "Jonah", "tlg041"),
    ("MIC", "Micah", "tlg038"), ("NAM", "Nahum", "tlg042"),
    ("HAB", "Habakkuk", "tlg043"), ("ZEP", "Zephaniah", "tlg044"),
    ("HAG", "Haggai", "tlg045"), ("ZEC", "Zechariah", "tlg046"),
    ("MAL", "Malachi", "tlg047"),
]


class BuildError(RuntimeError):
    pass


def request_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Mercy-Logos-LXX-Full/2.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=90) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    raise BuildError(f"failed to download {url}: {last_error}")


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def fetch_first1k_tree() -> dict[str, str]:
    raw = request_bytes(
        f"https://api.github.com/repos/{FIRST1K_REPOSITORY}/git/trees/{FIRST1K_TREE_SHA}?recursive=1"
    )
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot decode pinned First1K tree: {exc}") from exc
    if data.get("sha") != FIRST1K_TREE_SHA or data.get("truncated"):
        raise BuildError("pinned First1K Septuagint tree identity/truncation failure")
    return {
        str(row.get("path")): str(row.get("sha"))
        for row in (data.get("tree") or [])
        if row.get("type") == "blob" and HEX40.fullmatch(str(row.get("sha") or ""))
    }


def download_first1k(path: str, inventory: dict[str, str]) -> tuple[bytes, str, str]:
    expected_blob = inventory.get(path)
    if not expected_blob:
        raise BuildError(f"pinned First1K tree does not contain {path}")
    full_path = f"{FIRST1K_TREE_ROOT}/{path}"
    url = (
        f"https://raw.githubusercontent.com/{FIRST1K_REPOSITORY}/{FIRST1K_COMMIT}/"
        f"{quote(full_path, safe='/')}"
    )
    payload = request_bytes(url)
    actual_blob = git_blob_sha1(payload)
    if actual_blob != expected_blob:
        raise BuildError(
            f"Git blob mismatch for {full_path}: expected {expected_blob}, got {actual_blob}"
        )
    return payload, expected_blob, hashlib.sha256(payload).hexdigest()


def download_pinned(repo: str, commit: str, path: str, expected_blob: str) -> tuple[bytes, str]:
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{quote(path, safe='/')}"
    payload = request_bytes(url)
    actual_blob = git_blob_sha1(payload)
    if actual_blob != expected_blob:
        raise BuildError(
            f"Git blob mismatch for {repo}/{path}: expected {expected_blob}, got {actual_blob}"
        )
    return payload, hashlib.sha256(payload).hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def parse_metadata(payload: bytes, work: str) -> tuple[str, str]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise BuildError(f"{work}: invalid CTS metadata XML: {exc}") from exc
    expected_work_urn = f"urn:cts:greekLit:tlg0527.{work}"
    if root.attrib.get("urn") != expected_work_urn:
        raise BuildError(f"{work}: CTS work URN mismatch")
    title = next(
        (
            " ".join("".join(node.itertext()).split())
            for node in root.iter()
            if local_name(node.tag) == "title"
        ),
        work,
    )
    edition_urn = f"{expected_work_urn}.1st1K-grc1"
    editions = {
        str(node.attrib.get("urn") or "")
        for node in root.iter()
        if local_name(node.tag) == "edition"
    }
    if edition_urn not in editions:
        raise BuildError(f"{work}: pinned grc1 CTS edition declaration missing")
    return title, edition_urn


def verify_first1k_license(root: ET.Element, book_id: str) -> None:
    for node in root.iter():
        if local_name(node.tag) not in {"licence", "license"}:
            continue
        text = " ".join("".join(node.itertext()).split())
        if (
            node.attrib.get("target") == FIRST1K_LICENSE_TARGET
            and "Attribution-ShareAlike 4.0" in text
        ):
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


def parse_first1k_tei(payload: bytes, edition_urn: str, book_id: str) -> list[dict]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise BuildError(f"{book_id}: invalid TEI XML: {exc}") from exc
    verify_first1k_license(root, book_id)
    edition_nodes = [
        node
        for node in root.iter()
        if local_name(node.tag) == "div"
        and node.attrib.get("type") == "edition"
        and node.attrib.get("n") == edition_urn
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
            row = {
                "source_chapter": chapter,
                "source_verse": verse,
                "source_reference": f"{chapter}:{verse}" if chapter is not None else verse,
                "surface": text,
            }
            if not text:
                row["source_empty_surface"] = True
            verses.append(row)
            return
        for child in list(node):
            walk(child, chapter)

    walk(edition_nodes[0])
    if not verses:
        raise BuildError(f"{book_id}: no verse divisions parsed")
    return verses


def parse_ecclesiastes_jsonl(payload: bytes) -> list[dict]:
    try:
        text = payload.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise BuildError(f"Ecclesiastes fallback is not UTF-8: {exc}") from exc
    verses: list[dict] = []
    seen: set[tuple[str, str]] = set()
    for line_number, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise BuildError(f"Ecclesiastes JSONL line {line_number} is invalid: {exc}") from exc
        if row.get("urn") != "septuaginta.ecclesiastes":
            raise BuildError("Ecclesiastes fallback URN changed")
        if row.get("edition") != "wikisource-lxx-ecclesiastes" or row.get("source") != "wikisource":
            raise BuildError("Ecclesiastes fallback edition/source identity changed")
        if row.get("license") != ECC_LICENSE_STRING:
            raise BuildError("Ecclesiastes fallback licence declaration changed")
        locus = str(row.get("locus") or "")
        match = re.fullmatch(r"(\d+)\.(\d+)", locus)
        if not match:
            raise BuildError(f"Ecclesiastes fallback locus is invalid: {locus!r}")
        chapter, verse = match.groups()
        key = (chapter, verse)
        if key in seen:
            raise BuildError(f"Ecclesiastes duplicate source locus {chapter}:{verse}")
        seen.add(key)
        surface = WHITESPACE.sub(" ", str(row.get("text") or "")).strip()
        if not surface:
            raise BuildError(f"Ecclesiastes {chapter}:{verse}: empty fallback surface")
        verses.append(
            {
                "source_chapter": chapter,
                "source_verse": verse,
                "source_reference": f"{chapter}:{verse}",
                "surface": surface,
            }
        )
    chapters = {row["source_chapter"] for row in verses}
    if len(verses) != 222 or chapters != {str(i) for i in range(1, 13)}:
        raise BuildError(
            f"Ecclesiastes fallback inventory changed: {len(verses)} verses, chapters={sorted(chapters)}"
        )
    return verses


def split_scope(book_id: str, verses: list[dict]) -> tuple[list[dict], dict]:
    if book_id == "EZR":
        rows = [
            v
            for v in verses
            if str(v.get("source_chapter") or "").isdigit()
            and 1 <= int(v["source_chapter"]) <= 10
        ]
        return rows, {
            "mode": "esdras-b-component",
            "source_chapter_start": 1,
            "source_chapter_end": 10,
            "canonical_chapter_offset": 0,
        }
    if book_id == "NEH":
        rows = [
            v
            for v in verses
            if str(v.get("source_chapter") or "").isdigit()
            and 11 <= int(v["source_chapter"]) <= 23
        ]
        return rows, {
            "mode": "esdras-b-component",
            "source_chapter_start": 11,
            "source_chapter_end": 23,
            "canonical_chapter_offset": 10,
        }
    return verses, {"mode": "source-reference-preserved", "canonical_chapter_offset": 0}


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def ecclesiastes_source(inventory: dict[str, str]) -> tuple[list[dict], dict]:
    metadata_path = "tlg030/__cts__.xml"
    metadata_bytes, metadata_blob, metadata_sha256 = download_first1k(metadata_path, inventory)
    title, declared_edition_urn = parse_metadata(metadata_bytes, "tlg030")
    expected_first1k_text_path = "tlg030/tlg0527.tlg030.1st1K-grc1.xml"
    if expected_first1k_text_path in inventory:
        raise BuildError(
            "Ecclesiastes fallback is no longer justified because the pinned First1K tree now contains the Greek text"
        )

    corpus_bytes, corpus_sha256 = download_pinned(
        ECC_REPOSITORY, ECC_COMMIT, ECC_PATH, ECC_GIT_BLOB_SHA1
    )
    license_bytes, license_sha256 = download_pinned(
        ECC_REPOSITORY, ECC_COMMIT, ECC_LICENSE_PATH, ECC_LICENSE_GIT_BLOB_SHA1
    )
    ingest_bytes, ingest_sha256 = download_pinned(
        ECC_REPOSITORY, ECC_COMMIT, ECC_INGEST_PATH, ECC_INGEST_GIT_BLOB_SHA1
    )
    if b"Creative Commons Attribution-ShareAlike 4.0 International" not in license_bytes:
        raise BuildError("Ecclesiastes fallback repository licence evidence changed")
    if ECC_LICENSE_STRING.encode("utf-8") not in ingest_bytes:
        raise BuildError("Ecclesiastes fallback ingest provenance/licence evidence changed")

    verses = parse_ecclesiastes_jsonl(corpus_bytes)
    source = {
        "source_family": "open-greek-wikisource-ecclesiastes",
        "work": "tlg030",
        "work_title": title,
        "declared_first1k_edition_urn": declared_edition_urn,
        "first1k_gap_verified": True,
        "first1k_expected_text_path": f"{FIRST1K_TREE_ROOT}/{expected_first1k_text_path}",
        "first1k_metadata_path": f"{FIRST1K_TREE_ROOT}/{metadata_path}",
        "first1k_metadata_git_blob_sha1": metadata_blob,
        "first1k_metadata_sha256": metadata_sha256,
        "repository": ECC_REPOSITORY,
        "commit": ECC_COMMIT,
        "path": ECC_PATH,
        "git_blob_sha1": ECC_GIT_BLOB_SHA1,
        "sha256": corpus_sha256,
        "edition": "wikisource-lxx-ecclesiastes",
        "source": "Greek Wikisource",
        "license": "CC BY-SA 4.0",
        "license_detail": ECC_LICENSE_STRING,
        "license_evidence_path": ECC_LICENSE_PATH,
        "license_evidence_git_blob_sha1": ECC_LICENSE_GIT_BLOB_SHA1,
        "license_evidence_sha256": license_sha256,
        "ingest_evidence_path": ECC_INGEST_PATH,
        "ingest_evidence_git_blob_sha1": ECC_INGEST_GIT_BLOB_SHA1,
        "ingest_evidence_sha256": ingest_sha256,
        "recension_note": (
            "Ecclesiastical/Byzantine-tradition LXX transcription; not the Swete diplomatic Vaticanus text. "
            "Native Wikisource numbering is preserved."
        ),
        "per_file_license_verified": True,
    }
    return verses, source


def first1k_source(
    book_id: str, work: str, inventory: dict[str, str]
) -> tuple[list[dict], dict]:
    metadata_path = f"{work}/__cts__.xml"
    metadata_bytes, metadata_blob, metadata_sha256 = download_first1k(metadata_path, inventory)
    title, edition_urn = parse_metadata(metadata_bytes, work)
    text_path = f"{work}/tlg0527.{work}.1st1K-grc1.xml"
    text_bytes, text_blob, text_sha256 = download_first1k(text_path, inventory)
    verses = parse_first1k_tei(text_bytes, edition_urn, book_id)
    return verses, {
        "source_family": "first1k-swete",
        "work": work,
        "work_title": title,
        "edition_urn": edition_urn,
        "repository": FIRST1K_REPOSITORY,
        "commit": FIRST1K_COMMIT,
        "metadata_path": f"{FIRST1K_TREE_ROOT}/{metadata_path}",
        "metadata_git_blob_sha1": metadata_blob,
        "metadata_sha256": metadata_sha256,
        "text_path": f"{FIRST1K_TREE_ROOT}/{text_path}",
        "text_git_blob_sha1": text_blob,
        "text_sha256": text_sha256,
        "license": "CC BY-SA 4.0",
        "per_file_license_verified": True,
    }


def build(output: Path) -> dict:
    if len(WORKS) != 39 or len({row[0] for row in WORKS}) != 39:
        raise BuildError("protocanonical Greek contract must contain exactly 39 Catholic book scopes")
    inventory = fetch_first1k_tree()
    if output.exists():
        shutil.rmtree(output)
    book_dir = output / ISOLATED_ROOT / "books"
    book_dir.mkdir(parents=True, exist_ok=True)

    cache: dict[str, tuple[list[dict], dict]] = {}
    stats: list[dict] = []
    empty_loci: list[dict] = []
    total_verses = 0

    for book_id, canonical_name, work in WORKS:
        cache_key = "ECC-FALLBACK" if book_id == "ECC" else work
        if cache_key not in cache:
            if book_id == "ECC":
                cache[cache_key] = ecclesiastes_source(inventory)
            else:
                cache[cache_key] = first1k_source(book_id, work, inventory)
        source_verses, source_meta = cache[cache_key]
        verses, mapping = split_scope(book_id, source_verses)
        if not verses:
            raise BuildError(f"{book_id}: source split produced no verses")
        book_empty = [v for v in verses if v.get("source_empty_surface") is True]
        empty_loci.extend(
            {"book_id": book_id, "source_reference": v.get("source_reference")}
            for v in book_empty
        )
        payload = {
            "schema_version": 1,
            "corpus_id": "grc_ot_catholic_full",
            "corpus_version": CORPUS_VERSION,
            "production_enabled": True,
            "partition": "sharealike-catholic-lxx",
            "license": "CC BY-SA 4.0",
            "share_alike": True,
            "isolation_required": True,
            "book_id": book_id,
            "book": canonical_name,
            "language": "grc",
            "mapping": mapping,
            "source": source_meta,
            "surface_policy": {
                "source_boundaries_preserved": True,
                "empty_source_divisions_preserved": True,
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
        write_json(book_dir / f"{book_id}.json", payload)
        chapters = {
            v.get("source_chapter")
            for v in verses
            if v.get("source_chapter") is not None
        }
        stats.append(
            {
                "book_id": book_id,
                "book": canonical_name,
                "work": work,
                "source_family": source_meta["source_family"],
                "chapter_count": len(chapters),
                "verse_count": len(verses),
                "empty_source_surface_count": len(book_empty),
                "mapping": mapping,
            }
        )
        total_verses += len(verses)

    manifest = {
        "schema_version": 1,
        "corpus_id": "grc_ot_catholic_full",
        "corpus_version": CORPUS_VERSION,
        "status": "production-installed",
        "production_enabled": True,
        "language": "grc",
        "scope": (
            "39 protocanonical Catholic Old Testament book scopes: 38 pinned First1KGreek Swete scopes "
            "plus the pinned Greek Wikisource Ecclesiastes fallback; complements the accepted Catholic "
            "deuterocanonical/additions package"
        ),
        "book_count": 39,
        "first1k_swete_book_scope_count": 38,
        "ecclesiastes_fallback_book_scope_count": 1,
        "verse_record_count": total_verses,
        "empty_source_surface_count": len(empty_loci),
        "empty_source_surfaces": empty_loci,
        "books": stats,
        "sources": {
            "first1k_swete": {
                "repository": FIRST1K_REPOSITORY,
                "commit": FIRST1K_COMMIT,
                "septuagint_path": FIRST1K_TREE_ROOT,
                "septuagint_tree_sha": FIRST1K_TREE_SHA,
                "license": "CC BY-SA 4.0",
                "license_target": FIRST1K_LICENSE_TARGET,
                "share_alike": True,
                "isolation_required": True,
                "attribution": "OpenGreekAndLatin First1KGreek / Henry Barclay Swete Septuagint witnesses.",
            },
            "ecclesiastes": {
                "repository": ECC_REPOSITORY,
                "commit": ECC_COMMIT,
                "path": ECC_PATH,
                "git_blob_sha1": ECC_GIT_BLOB_SHA1,
                "license": "CC BY-SA 4.0",
                "license_detail": ECC_LICENSE_STRING,
                "share_alike": True,
                "isolation_required": True,
                "source": "Greek Wikisource via Open Greek Corpus",
                "recension": "ecclesiastical/Byzantine-tradition LXX",
                "verse_count": 222,
                "chapter_count": 12,
                "first1k_gap_verified": True,
            },
        },
        "partition": {
            "path": ISOLATED_ROOT,
            "license": "CC BY-SA 4.0",
            "share_alike": True,
            "isolation_required": True,
        },
        "runtime_contract": {
            "local_only": True,
            "source_boundaries_preserved": True,
            "empty_source_divisions_preserved": True,
            "automatic_versification_remapping": False,
            "exact_douay_rheims_alignment_required_before_parallel_render": True,
            "deuterocanonical_package": "grc_ot_catholic_swete",
            "daniel_primary_base_witness": "Theodotion",
            "ezra_nehemiah_source": "Esdras B",
            "ecclesiastes_source": "Greek Wikisource ecclesiastical LXX via pinned Open Greek Corpus",
            "ecclesiastes_not_swete": True,
        },
        "derived_layers": {
            "glosses": False,
            "lemmata": False,
            "morphology": False,
            "transliteration": False,
        },
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = build(args.output.resolve())
    print(
        f"[OT Greek Full] vendored {manifest['book_count']} book scopes / "
        f"{manifest['verse_record_count']} source verse records / "
        f"{manifest['empty_source_surface_count']} preserved empty First1K source divisions; "
        "Ecclesiastes supplied by pinned Greek Wikisource fallback"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        raise SystemExit(f"OT Greek full build failed: {exc}") from exc
