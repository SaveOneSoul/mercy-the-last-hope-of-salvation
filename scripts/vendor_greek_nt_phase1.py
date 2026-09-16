#!/usr/bin/env python3
"""Build the validation-only 27-book Greek NT interlinear source layers.

SBLGNT surface text (CC BY 4.0) and MorphGNT linguistic annotations
(CC BY-SA 3.0) remain in separate output partitions. Every upstream file is
verified by pinned Git blob SHA-1 before parsing. Source surfaces are preserved
verbatim; comparison-only normalization removes presentation punctuation,
known apparatus/elision marks, and case distinctions while preserving Greek
letters and diacritics. Any remaining lexical difference fails the build.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "greek_nt_phase1" / "source-lock.json"
DEFAULT_OUTPUT = ROOT / "build" / "logos-greek-nt-phase1"
VERSE_REF_RE = re.compile(r"^(.+?)\s+(\d+):(\d+)$")
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
APPARATUS_MARKERS = frozenset({"⸀", "⸂", "⸃"})
ELISION_MARKERS = frozenset({"ʼ", "’"})

GREEK_MAP = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z",
    "η": "ē", "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m",
    "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s",
    "ς": "s", "τ": "t", "υ": "y", "φ": "ph", "χ": "ch", "ψ": "ps",
    "ω": "ō",
}
ROUGH_BREATHING = "\u0314"
IOTA_SUBSCRIPT = "\u0345"


class BuildError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read {path}: {exc}") from exc


def git_blob_sha1(payload: bytes) -> str:
    prefix = f"blob {len(payload)}\0".encode("ascii")
    return hashlib.sha1(prefix + payload).hexdigest()


def download_pinned(repo: str, commit: str, path: str, expected_blob_sha1: str) -> tuple[str, str]:
    if not HEX40_RE.fullmatch(expected_blob_sha1):
        raise BuildError(f"invalid expected Git blob SHA-1 for {repo}:{path}")
    encoded_path = quote(path, safe="/")
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{encoded_path}"
    request = Request(url, headers={"User-Agent": "Mercy-Logos-Greek-NT-Phase1/1.0"})
    last_error: Exception | None = None
    payload: bytes | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=45) as response:
                payload = response.read()
            break
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    if payload is None:
        raise BuildError(f"failed to download {repo}:{path}: {last_error}")
    actual_blob = git_blob_sha1(payload)
    if actual_blob != expected_blob_sha1:
        raise BuildError(
            f"Git blob mismatch for {repo}:{path}: expected {expected_blob_sha1}, got {actual_blob}"
        )
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BuildError(f"source is not UTF-8: {repo}:{path}") from exc
    return text, hashlib.sha256(payload).hexdigest()


def parse_sblgnt(text: str, book_name: str) -> dict[tuple[int, int], str]:
    verses: dict[tuple[int, int], str] = {}
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.rstrip()
        if not line or "\t" not in line:
            continue
        ref_text, verse_text = line.split("\t", 1)
        match = VERSE_REF_RE.fullmatch(ref_text.strip())
        if not match:
            raise BuildError(f"{book_name}: malformed SBLGNT verse reference on line {line_no}: {ref_text!r}")
        chapter = int(match.group(2))
        verse = int(match.group(3))
        verse_text = verse_text.strip()
        if not verse_text:
            raise BuildError(f"{book_name} {chapter}:{verse}: empty SBLGNT verse")
        key = (chapter, verse)
        if key in verses:
            raise BuildError(f"{book_name} {chapter}:{verse}: duplicate SBLGNT verse")
        verses[key] = verse_text
    if not verses:
        raise BuildError(f"{book_name}: no SBLGNT verses parsed")
    return verses


def parse_morphgnt(text: str, book_name: str) -> dict[tuple[int, int], list[dict]]:
    verses: dict[tuple[int, int], list[dict]] = defaultdict(list)
    for line_no, raw in enumerate(text.splitlines(), start=1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(maxsplit=6)
        if len(parts) != 7:
            raise BuildError(f"{book_name}: malformed MorphGNT row on line {line_no}")
        source_ref, pos_code, morphology, surface, source_word, normalized, lemma = parts
        if len(source_ref) != 6 or not source_ref.isdigit():
            raise BuildError(f"{book_name}: invalid MorphGNT reference {source_ref!r} on line {line_no}")
        chapter = int(source_ref[2:4])
        verse = int(source_ref[4:6])
        key = (chapter, verse)
        position = len(verses[key]) + 1
        verses[key].append(
            {
                "source_ref": source_ref,
                "position": position,
                "surface": surface,
                "source_word": source_word,
                "normalized": normalized,
                "lemma": lemma,
                "part_of_speech_code": pos_code,
                "morphology": morphology,
            }
        )
    if not verses:
        raise BuildError(f"{book_name}: no MorphGNT rows parsed")
    return dict(verses)


def lexical_alignment_key(value: str) -> str:
    """Return a comparison-only Greek lexical core; source text is never changed."""
    normalized = unicodedata.normalize("NFC", value).casefold()
    normalized = unicodedata.normalize("NFC", normalized)
    chars: list[str] = []
    for char in normalized:
        if char in APPARATUS_MARKERS or char in ELISION_MARKERS:
            continue
        if unicodedata.category(char).startswith("P"):
            continue
        chars.append(char)
    return "".join(chars)


def classify_surface_alignment(sbl_surface: str, morph_surface: str) -> str:
    if sbl_surface == morph_surface:
        return "exact"
    sbl_key = lexical_alignment_key(sbl_surface)
    morph_key = lexical_alignment_key(morph_surface)
    if sbl_key and sbl_key == morph_key:
        return "source-presentation-normalized"
    raise BuildError(
        "surface tokens differ lexically after presentation-only normalization: "
        f"SBLGNT={sbl_surface!r} ({sbl_key!r}), MorphGNT={morph_surface!r} ({morph_key!r})"
    )


def transliterate_greek(surface: str) -> str:
    decomposed = unicodedata.normalize("NFD", surface)
    rough = ROUGH_BREATHING in decomposed
    first_base_upper = False
    base_seen = False
    out: list[str] = []
    for char in decomposed:
        if char == IOTA_SUBSCRIPT:
            out.append("i")
            continue
        if unicodedata.category(char).startswith("M"):
            continue
        mapped = GREEK_MAP.get(char.lower())
        if mapped is None:
            continue
        if not base_seen:
            first_base_upper = char.isupper()
            base_seen = True
        out.append(mapped)
    result = "".join(out)
    if rough and result:
        result = ("rh" + result[1:]) if result.startswith("r") else ("h" + result)
    if first_base_upper and result:
        result = result[0].upper() + result[1:]
    return result


def token_id(book_id: str, chapter: int, verse: int, position: int) -> str:
    return f"{book_id}-{chapter}-{verse}-GR-{position:03d}"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def comparison_policy() -> dict:
    return {
        "unicode_normalization": "NFC",
        "casefolded_for_comparison": True,
        "ignored_apparatus_markers": sorted(APPARATUS_MARKERS),
        "ignored_elision_markers": sorted(ELISION_MARKERS),
        "ignored_unicode_categories": ["P*"],
        "preserved_for_comparison": ["Greek letters", "combining marks"],
        "source_surfaces_preserved": True,
    }


def build_book(book: dict, lock: dict, output: Path) -> dict:
    book_id = str(book["book_id"])
    book_name = str(book["name"])
    sbl_source = lock["sources"]["sblgnt"]
    morph_source = lock["sources"]["morphgnt"]

    sbl_text, sbl_sha256 = download_pinned(
        sbl_source["repository"], sbl_source["commit"],
        book["sblgnt"]["path"], book["sblgnt"]["blob_sha1"],
    )
    morph_text, morph_sha256 = download_pinned(
        morph_source["repository"], morph_source["commit"],
        book["morphgnt"]["path"], book["morphgnt"]["blob_sha1"],
    )

    sbl_verses = parse_sblgnt(sbl_text, book_name)
    morph_verses = parse_morphgnt(morph_text, book_name)
    if set(sbl_verses) != set(morph_verses):
        missing_morph = sorted(set(sbl_verses) - set(morph_verses))
        missing_surface = sorted(set(morph_verses) - set(sbl_verses))
        raise BuildError(
            f"{book_name}: verse inventory mismatch; "
            f"missing MorphGNT={missing_morph[:8]}, missing SBLGNT={missing_surface[:8]}"
        )

    surface_chapters: dict[str, dict] = {}
    linguistic_chapters: dict[str, dict] = {}
    alignment_verses: list[dict] = []
    token_total = exact_token_total = normalized_token_total = 0
    exact_verse_total = normalized_verse_total = 0

    for chapter, verse in sorted(sbl_verses):
        text = sbl_verses[(chapter, verse)]
        surfaces = text.split()
        morph_rows = morph_verses[(chapter, verse)]
        if len(surfaces) != len(morph_rows):
            raise BuildError(
                f"{book_name} {chapter}:{verse}: token-count mismatch; "
                f"SBLGNT count={len(surfaces)}, MorphGNT count={len(morph_rows)}"
            )

        surface_tokens: list[dict] = []
        linguistic_tokens: list[dict] = []
        ids: list[str] = []
        verse_exact = verse_normalized = 0

        for position, (surface, morph_row) in enumerate(zip(surfaces, morph_rows), start=1):
            try:
                alignment_mode = classify_surface_alignment(surface, morph_row["surface"])
            except BuildError as exc:
                raise BuildError(f"{book_name} {chapter}:{verse} token {position}: {exc}") from exc
            if alignment_mode == "exact":
                verse_exact += 1
            else:
                verse_normalized += 1

            current_id = token_id(book_id, chapter, verse, position)
            transliteration = transliterate_greek(surface)
            if not transliteration:
                raise BuildError(f"{book_name} {chapter}:{verse} token {position}: transliteration is empty")
            ids.append(current_id)
            surface_tokens.append(
                {
                    "id": current_id,
                    "position": position,
                    "surface": surface,
                    "transliteration": transliteration,
                }
            )
            linguistic_tokens.append(
                {
                    "id": current_id,
                    "position": position,
                    "source_token_id": f"{morph_row['source_ref']}:{position:03d}",
                    "source_surface": morph_row["surface"],
                    "part_of_speech_code": morph_row["part_of_speech_code"],
                    "morphology": morph_row["morphology"],
                    "normalized": morph_row["normalized"],
                    "lemma": morph_row["lemma"],
                    "alignment_mode": alignment_mode,
                }
            )

        surface_chapters.setdefault(str(chapter), {})[str(verse)] = {
            "text": text,
            "tokens": surface_tokens,
        }
        linguistic_chapters.setdefault(str(chapter), {})[str(verse)] = {
            "tokens": linguistic_tokens,
        }
        verse_mode = "exact" if verse_normalized == 0 else "source-presentation-normalized"
        alignment_verses.append(
            {
                "chapter": chapter,
                "verse": str(verse),
                "token_count": len(ids),
                "token_ids": ids,
                "alignment_mode": verse_mode,
                "exact_token_count": verse_exact,
                "source_presentation_normalized_token_count": verse_normalized,
                "lexical_mismatch_count": 0,
            }
        )

        token_total += len(ids)
        exact_token_total += verse_exact
        normalized_token_total += verse_normalized
        if verse_mode == "exact":
            exact_verse_total += 1
        else:
            normalized_verse_total += 1

    surface_payload = {
        "schema_version": 1,
        "phase": lock["phase"],
        "status": "validation-only",
        "layer": "surface",
        "book_id": book_id,
        "name": book_name,
        "language": "grc",
        "source": {
            "id": "sblgnt",
            "repository": sbl_source["repository"],
            "commit": sbl_source["commit"],
            "path": book["sblgnt"]["path"],
            "blob_sha1": book["sblgnt"]["blob_sha1"],
            "sha256": sbl_sha256,
            "license": sbl_source["license"],
        },
        "derived_fields": {
            "transliteration": {
                "source": "logos-derived-greek-transliteration-v1",
                "basis": "SBLGNT surface token",
                "note": "Mechanical deterministic transliteration for search/display; not a replacement for the Greek source.",
            }
        },
        "chapters": surface_chapters,
    }
    linguistic_payload = {
        "schema_version": 1,
        "phase": lock["phase"],
        "status": "validation-only",
        "layer": "linguistics",
        "book_id": book_id,
        "name": book_name,
        "language": "grc",
        "source": {
            "id": "morphgnt-sblgnt",
            "repository": morph_source["repository"],
            "commit": morph_source["commit"],
            "path": book["morphgnt"]["path"],
            "blob_sha1": book["morphgnt"]["blob_sha1"],
            "sha256": morph_sha256,
            "license": morph_source["license"],
            "share_alike": True,
            "isolation_required": True,
        },
        "field_provenance": {
            "source_surface": "MorphGNT",
            "lemma": "MorphGNT",
            "normalized": "MorphGNT",
            "part_of_speech_code": "MorphGNT",
            "morphology": "MorphGNT",
            "alignment_mode": "project-generated comparison of preserved source surfaces",
        },
        "chapters": linguistic_chapters,
    }
    alignment_payload = {
        "schema_version": 1,
        "phase": lock["phase"],
        "status": "validation-only",
        "layer": "alignment",
        "book_id": book_id,
        "name": book_name,
        "contains_source_text": False,
        "contains_linguistic_payload": False,
        "verse_count": len(alignment_verses),
        "token_count": token_total,
        "exact_token_count": exact_token_total,
        "source_presentation_normalized_token_count": normalized_token_total,
        "exact_verse_count": exact_verse_total,
        "source_presentation_normalized_verse_count": normalized_verse_total,
        "lexical_mismatch_count": 0,
        "alignment_mismatch_count": 0,
        "comparison_policy": comparison_policy(),
        "verses": alignment_verses,
    }

    write_json(output / "surface" / f"{book_id}.json", surface_payload)
    write_json(output / "linguistics" / f"{book_id}.json", linguistic_payload)
    write_json(output / "alignment" / f"{book_id}.json", alignment_payload)

    return {
        "order": int(book["order"]),
        "book_id": book_id,
        "name": book_name,
        "chapter_count": len({chapter for chapter, _ in sbl_verses}),
        "verse_count": len(sbl_verses),
        "token_count": token_total,
        "exact_token_count": exact_token_total,
        "source_presentation_normalized_token_count": normalized_token_total,
        "exact_verse_count": exact_verse_total,
        "source_presentation_normalized_verse_count": normalized_verse_total,
        "lexical_mismatch_count": 0,
        "alignment_mismatch_count": 0,
        "sblgnt": {
            "path": book["sblgnt"]["path"],
            "blob_sha1": book["sblgnt"]["blob_sha1"],
            "sha256": sbl_sha256,
        },
        "morphgnt": {
            "path": book["morphgnt"]["path"],
            "blob_sha1": book["morphgnt"]["blob_sha1"],
            "sha256": morph_sha256,
        },
    }


def validate_lock(lock: dict) -> None:
    if lock.get("phase") != "Greek NT Expansion Phase 1":
        raise BuildError("unexpected phase name")
    if lock.get("production", {}).get("enabled") is not False:
        raise BuildError("Phase 1 importer must remain non-production")
    if lock.get("owner_acceptance", {}).get("accepted") is not True:
        raise BuildError("owner acceptance for the John 1:1 prototype is not recorded")
    books = lock.get("books") or []
    if len(books) != 27:
        raise BuildError(f"source lock must contain exactly 27 NT books, found {len(books)}")
    if [row.get("order") for row in books] != list(range(1, 28)):
        raise BuildError("source lock book order must be 1..27")
    if len({row.get("book_id") for row in books}) != 27:
        raise BuildError("source lock book ids are not unique")
    sbl = lock.get("sources", {}).get("sblgnt", {})
    morph = lock.get("sources", {}).get("morphgnt", {})
    if sbl.get("license") != "CC BY 4.0":
        raise BuildError("SBLGNT licence lock changed")
    if "CC BY-SA 3.0" not in str(morph.get("license")):
        raise BuildError("MorphGNT licence lock changed")
    if morph.get("share_alike") is not True or morph.get("isolation_required") is not True:
        raise BuildError("MorphGNT ShareAlike isolation is not enabled")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--keep-output", action="store_true")
    args = parser.parse_args()

    lock = load_json(LOCK_PATH)
    validate_lock(lock)
    output = args.output.resolve()
    if output == ROOT.resolve():
        raise BuildError("refusing to use repository root as output directory")
    if output.exists() and not args.keep_output:
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    book_stats = []
    for book in lock["books"]:
        print(f"[Greek NT Phase 1] {book['order']:02d}/27 {book['name']}")
        book_stats.append(build_book(book, lock, output))

    manifest = {
        "schema_version": 1,
        "phase": lock["phase"],
        "status": "validation-generated",
        "production_enabled": False,
        "book_count": len(book_stats),
        "chapter_count": sum(row["chapter_count"] for row in book_stats),
        "verse_count": sum(row["verse_count"] for row in book_stats),
        "token_count": sum(row["token_count"] for row in book_stats),
        "exact_token_count": sum(row["exact_token_count"] for row in book_stats),
        "source_presentation_normalized_token_count": sum(
            row["source_presentation_normalized_token_count"] for row in book_stats
        ),
        "exact_alignment_verse_count": sum(row["exact_verse_count"] for row in book_stats),
        "source_presentation_normalized_verse_count": sum(
            row["source_presentation_normalized_verse_count"] for row in book_stats
        ),
        "lexical_mismatch_count": sum(row["lexical_mismatch_count"] for row in book_stats),
        "alignment_mismatch_count": sum(row["alignment_mismatch_count"] for row in book_stats),
        "alignment_policy": {
            "mode": "exact-or-lexical-core-with-source-presentation-ignored",
            **comparison_policy(),
        },
        "source_commits": {
            "sblgnt": lock["sources"]["sblgnt"]["commit"],
            "morphgnt": lock["sources"]["morphgnt"]["commit"],
        },
        "license_partitions": lock["license_partitions"],
        "gloss_layer": {
            "installed": False,
            "reason": "Phase 1 does not invent or copy glosses; a separately approved gloss source is required.",
        },
        "books": book_stats,
    }
    write_json(output / "manifest.json", manifest)

    print(
        "[Greek NT Phase 1] generated "
        f"{manifest['book_count']} books, {manifest['chapter_count']} chapters, "
        f"{manifest['verse_count']} verses, {manifest['token_count']} aligned tokens "
        f"({manifest['source_presentation_normalized_token_count']} presentation-normalized); "
        "production remains disabled"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        raise SystemExit(f"Greek NT Phase 1 build failed: {exc}") from exc
