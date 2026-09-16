#!/usr/bin/env python3
"""Build the validation-only Logos Old Testament Phase 1A corpus.

The source is the pinned Open Scriptures Hebrew Bible (OSHB) / Westminster
Leningrad Codex tree. Source Hebrew and Aramaic strings are preserved verbatim:
this importer intentionally performs no Unicode normalization. Lemma and
morphology annotations remain a separate CC BY 4.0 partition from the
public-domain WLC surface text.

This phase covers the 39 Masoretic/Hebrew-Bible witnesses only. It does not
claim a complete Catholic 46-book Old Testament original-language corpus.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
import xml.etree.ElementTree as ET
from collections import defaultdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = (
    ROOT
    / "cloud-backend"
    / "app"
    / "logos_interlinear"
    / "old_testament_phase1"
    / "source-lock.json"
)
DEFAULT_OUTPUT = ROOT / "build" / "logos-old-testament-phase1"
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
VERSE_RE = re.compile(r"^([1-4]?[A-Za-z]+)\.(\d+)\.(\d+)$")


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


def git_blob_sha1(payload: bytes) -> str:
    prefix = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(prefix + payload).hexdigest()


def request_bytes(url: str, user_agent: str) -> bytes:
    request = Request(url, headers={"User-Agent": user_agent, "Accept": "application/vnd.github+json"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=60) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    raise BuildError(f"failed to download {url}: {last_error}")


def fetch_locked_tree(repo: str, tree_sha: str) -> dict[str, str]:
    if not HEX40_RE.fullmatch(tree_sha):
        raise BuildError("invalid locked OSHB tree SHA")
    url = f"https://api.github.com/repos/{repo}/git/trees/{tree_sha}"
    payload = request_bytes(url, "Mercy-Logos-OT-Phase1A/1.0")
    try:
        data = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot decode locked OSHB tree response: {exc}") from exc
    if data.get("sha") != tree_sha:
        raise BuildError(f"OSHB tree identity mismatch: expected {tree_sha}, got {data.get('sha')}")
    if data.get("truncated"):
        raise BuildError("locked OSHB wlc tree response is unexpectedly truncated")
    inventory: dict[str, str] = {}
    for row in data.get("tree") or []:
        path = str(row.get("path") or "")
        sha = str(row.get("sha") or "")
        if row.get("type") != "blob" or not path.endswith(".xml"):
            continue
        if not HEX40_RE.fullmatch(sha):
            raise BuildError(f"invalid Git blob SHA for locked source file {path}")
        if path in inventory:
            raise BuildError(f"duplicate source path in locked OSHB tree: {path}")
        inventory[path] = sha
    return inventory


def download_pinned(repo: str, commit: str, directory: str, filename: str, expected_blob_sha1: str) -> tuple[bytes, str]:
    if not HEX40_RE.fullmatch(commit) or not HEX40_RE.fullmatch(expected_blob_sha1):
        raise BuildError(f"invalid immutable source pin for {filename}")
    path = f"{directory.rstrip('/')}/{filename}"
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{quote(path, safe='/')}"
    payload = request_bytes(url, "Mercy-Logos-OT-Phase1A/1.0")
    actual_blob = git_blob_sha1(payload)
    if actual_blob != expected_blob_sha1:
        raise BuildError(
            f"Git blob mismatch for {path}: expected {expected_blob_sha1}, got {actual_blob}"
        )
    return payload, hashlib.sha256(payload).hexdigest()


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def token_language(morphology: str, reference: str, position: int) -> str:
    if morphology.startswith("H"):
        return "he"
    if morphology.startswith("A"):
        return "arc"
    raise BuildError(
        f"{reference} token {position}: morphology does not declare Hebrew/Aramaic language: {morphology!r}"
    )


def token_id(book_id: str, chapter: int, verse: int, position: int) -> str:
    return f"{book_id}-{chapter}-{verse}-SEMITIC-{position:03d}"


def parse_book(payload: bytes, book: dict, expected_blob_sha1: str, sha256: str) -> tuple[dict, dict, dict, dict]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise BuildError(f"{book['name']}: invalid OSIS XML: {exc}") from exc

    book_id = str(book["book_id"])
    book_name = str(book["name"])
    source_osis = str(book["source_osis"])
    surface_chapters: dict[str, dict] = {}
    linguistic_chapters: dict[str, dict] = {}
    alignment_verses: list[dict] = []
    chapter_ids: set[int] = set()
    seen_refs: set[tuple[int, int]] = set()
    token_total = hebrew_tokens = aramaic_tokens = verse_total = 0

    for verse_el in root.iter():
        if local_name(verse_el.tag) != "verse":
            continue
        osis_id = str(verse_el.attrib.get("osisID") or "")
        match = VERSE_RE.fullmatch(osis_id)
        if not match:
            raise BuildError(f"{book_name}: malformed or missing verse osisID {osis_id!r}")
        if match.group(1) != source_osis:
            raise BuildError(
                f"{book_name}: source OSIS book mismatch; expected {source_osis}, got {match.group(1)}"
            )
        chapter = int(match.group(2))
        verse = int(match.group(3))
        key = (chapter, verse)
        if key in seen_refs:
            raise BuildError(f"{book_name} {chapter}:{verse}: duplicate verse")
        seen_refs.add(key)
        chapter_ids.add(chapter)

        surface_tokens: list[dict] = []
        linguistic_tokens: list[dict] = []
        token_ids: list[str] = []
        verse_languages: set[str] = set()

        # Canonical tokens are direct verse-child <w> nodes only. Nested qere or
        # other variant <w> nodes inside <note>/<rdg> are deliberately excluded.
        for child in list(verse_el):
            if local_name(child.tag) != "w":
                continue
            position = len(surface_tokens) + 1
            surface = child.text
            if surface is None or surface == "":
                raise BuildError(f"{book_name} {chapter}:{verse} token {position}: empty surface")
            lemma = str(child.attrib.get("lemma") or "")
            morphology = str(child.attrib.get("morph") or "")
            source_word_id = str(child.attrib.get("id") or "")
            if not lemma:
                raise BuildError(f"{book_name} {chapter}:{verse} token {position}: missing lemma")
            if not morphology:
                raise BuildError(f"{book_name} {chapter}:{verse} token {position}: missing morphology")
            if not source_word_id:
                raise BuildError(f"{book_name} {chapter}:{verse} token {position}: missing source word id")
            language = token_language(morphology, f"{book_name} {chapter}:{verse}", position)
            current_id = token_id(book_id, chapter, verse, position)
            token_ids.append(current_id)
            verse_languages.add(language)
            if language == "he":
                hebrew_tokens += 1
            else:
                aramaic_tokens += 1

            surface_tokens.append(
                {
                    "id": current_id,
                    "position": position,
                    "surface": surface,
                    "language": language,
                }
            )
            linguistic = {
                "id": current_id,
                "position": position,
                "source_word_id": source_word_id,
                "lemma": lemma,
                "morphology": morphology,
                "language": language,
            }
            if child.attrib.get("type"):
                linguistic["source_type"] = str(child.attrib["type"])
            if child.attrib.get("n"):
                linguistic["source_n"] = str(child.attrib["n"])
            linguistic_tokens.append(linguistic)

        if not surface_tokens:
            raise BuildError(f"{book_name} {chapter}:{verse}: no direct canonical word tokens")
        if len(surface_tokens) != len(linguistic_tokens):
            raise BuildError(f"{book_name} {chapter}:{verse}: internal token partition mismatch")

        surface_chapters.setdefault(str(chapter), {})[str(verse)] = {
            "source_osis_id": osis_id,
            "languages": sorted(verse_languages),
            "tokens": surface_tokens,
        }
        linguistic_chapters.setdefault(str(chapter), {})[str(verse)] = {
            "source_osis_id": osis_id,
            "languages": sorted(verse_languages),
            "tokens": linguistic_tokens,
        }
        alignment_verses.append(
            {
                "chapter": chapter,
                "verse": str(verse),
                "source_osis_id": osis_id,
                "token_count": len(token_ids),
                "token_ids": token_ids,
                "alignment_mode": "same-source-exact-token-id",
                "mismatch_count": 0,
            }
        )
        token_total += len(token_ids)
        verse_total += 1

    if not seen_refs:
        raise BuildError(f"{book_name}: no verses parsed")

    source_record = {
        "id": "oshb",
        "repository": "openscriptures/morphhb",
        "commit": "3d15126fb1ef74867fc1434be1942e837932691f",
        "path": f"wlc/{book['filename']}",
        "git_blob_sha1": expected_blob_sha1,
        "sha256": sha256,
    }
    book_common = {
        "schema_version": 1,
        "phase": "Old Testament Expansion Phase 1A",
        "production_enabled": False,
        "book_id": book_id,
        "book": book_name,
        "catholic_order": int(book["catholic_order"]),
        "source_osis": source_osis,
        "source": source_record,
        "normalization_applied": False,
    }
    surface_payload = {
        **book_common,
        "partition": "surface",
        "rights": "Westminster Leningrad Codex — Public Domain",
        "chapters": surface_chapters,
    }
    linguistic_payload = {
        **book_common,
        "partition": "linguistics",
        "license": "CC BY 4.0",
        "attribution": "Open Scriptures Hebrew Bible Project",
        "chapters": linguistic_chapters,
    }
    alignment_payload = {
        **book_common,
        "partition": "alignment",
        "alignment_mode": "same-source-exact-token-id",
        "verses": alignment_verses,
        "mismatch_count": 0,
    }
    stats = {
        "book_id": book_id,
        "name": book_name,
        "catholic_order": int(book["catholic_order"]),
        "filename": str(book["filename"]),
        "source_git_blob_sha1": expected_blob_sha1,
        "source_sha256": sha256,
        "chapter_count": len(chapter_ids),
        "verse_count": verse_total,
        "token_count": token_total,
        "hebrew_token_count": hebrew_tokens,
        "aramaic_token_count": aramaic_tokens,
        "catholic_completeness": book.get("catholic_completeness", "masoretic-witness-complete"),
    }
    return surface_payload, linguistic_payload, alignment_payload, stats


def build(output: Path) -> dict:
    lock = load_json(LOCK_PATH)
    source = lock.get("source") or {}
    books = lock.get("books") or []
    if lock.get("production_enabled") is not False or lock.get("catholic_ot_complete") is not False:
        raise BuildError("Phase 1A source lock must remain validation-only and Catholic-OT-incomplete")
    if len(books) != 39:
        raise BuildError(f"Phase 1A requires exactly 39 source-book mappings, got {len(books)}")

    repo = str(source.get("repository") or "")
    commit = str(source.get("commit") or "")
    directory = str(source.get("directory") or "")
    tree_sha = str(source.get("tree_sha") or "")
    if repo != "openscriptures/morphhb" or not HEX40_RE.fullmatch(commit):
        raise BuildError("unexpected or invalid OSHB repository pin")

    inventory = fetch_locked_tree(repo, tree_sha)
    expected_inventory = {str(row["filename"]) for row in books}
    expected_inventory.update(str(x) for x in (lock.get("required_non_book_files") or []))
    actual_inventory = set(inventory)
    if actual_inventory != expected_inventory:
        missing = sorted(expected_inventory - actual_inventory)
        extra = sorted(actual_inventory - expected_inventory)
        raise BuildError(f"locked OSHB XML inventory mismatch; missing={missing}, extra={extra}")

    if output.exists():
        shutil.rmtree(output)
    for partition in ("surface", "linguistics", "alignment"):
        (output / partition).mkdir(parents=True, exist_ok=True)

    book_stats: list[dict] = []
    totals = defaultdict(int)
    for book in books:
        filename = str(book["filename"])
        payload, sha256 = download_pinned(repo, commit, directory, filename, inventory[filename])
        surface, linguistics, alignment, stats = parse_book(payload, book, inventory[filename], sha256)
        book_id = str(book["book_id"])
        write_json(output / "surface" / f"{book_id}.json", surface)
        write_json(output / "linguistics" / f"{book_id}.json", linguistics)
        write_json(output / "alignment" / f"{book_id}.json", alignment)
        book_stats.append(stats)
        for field in ("chapter_count", "verse_count", "token_count", "hebrew_token_count", "aramaic_token_count"):
            totals[field] += int(stats[field])

    verse_map_payload, verse_map_sha256 = download_pinned(
        repo,
        commit,
        directory,
        "VerseMap.xml",
        inventory["VerseMap.xml"],
    )
    if not verse_map_payload:
        raise BuildError("locked OSHB VerseMap.xml is empty")

    manifest = {
        "schema_version": 1,
        "phase": "Old Testament Expansion Phase 1A",
        "production_enabled": False,
        "catholic_ot_complete": False,
        "masoretic_book_witness_count": len(book_stats),
        "chapter_count": totals["chapter_count"],
        "verse_count": totals["verse_count"],
        "token_count": totals["token_count"],
        "hebrew_token_count": totals["hebrew_token_count"],
        "aramaic_token_count": totals["aramaic_token_count"],
        "alignment_mismatch_count": 0,
        "surface_normalization_applied": False,
        "gloss_layer": {"installed": False},
        "transliteration_layer": {"installed": False},
        "dra_versification_alignment": {"enabled": False},
        "source": {
            "id": "oshb",
            "repository": repo,
            "commit": commit,
            "directory": directory,
            "tree_sha": tree_sha,
            "base_text": "Westminster Leningrad Codex",
            "base_text_rights": "Public Domain",
            "annotation_license": "CC BY 4.0",
            "attribution": "Open Scriptures Hebrew Bible Project",
            "verse_map_git_blob_sha1": inventory["VerseMap.xml"],
            "verse_map_sha256": verse_map_sha256,
        },
        "books": book_stats,
        "catholic_scope": {
            "excluded_pending_greek_material": lock.get("excluded_catholic_ot_material") or [],
            "esther_and_daniel_status": "Masoretic portions only; Catholic Greek additions pending separate source gate",
        },
    }
    write_json(output / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = build(args.output.resolve())
    print(
        "Built Logos OT Phase 1A: "
        f"{manifest['masoretic_book_witness_count']} books, "
        f"{manifest['chapter_count']} chapters, "
        f"{manifest['verse_count']} verses, "
        f"{manifest['token_count']} tokens "
        f"({manifest['hebrew_token_count']} Hebrew, {manifest['aramaic_token_count']} Aramaic)."
    )


if __name__ == "__main__":
    main()
