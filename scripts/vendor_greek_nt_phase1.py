#!/usr/bin/env python3
"""Build the validation-only 27-book Greek NT interlinear source layers.

This importer deliberately keeps SBLGNT surface text (CC BY 4.0) separate from
MorphGNT linguistic annotations (CC BY-SA 3.0). It verifies the immutable
Git blob SHA-1 for every downloaded source file before parsing, requires
word-for-word alignment, and writes no production API data.

Source text is always preserved verbatim. For alignment comparison only, two
narrow source-presentation normalizations are allowed: explicitly enumerated
SBLGNT textual-apparatus glyphs may be ignored, and explicitly enumerated
punctuation glyph pairs confirmed between the pinned sources may be treated as
equivalent. Greek letters, accents and breathing marks remain significant.
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
PUNCTUATION_EQUIVALENTS = {
    "ʼ": "’",  # U+02BC modifier apostrophe -> U+2019 right single quotation mark
    ";": ";",  # U+037E Greek question mark -> MorphGNT semicolon glyph
}

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
            if attempt == 2:
                break
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


def strip_apparatus_markers(value: str) -> str:
    """Remove only the SBLGNT apparatus glyphs explicitly approved for alignment."""
    return "".join(char for char in value if char not in APPARATUS_MARKERS)


def normalize_punctuation(value: str) -> str:
    """Canonicalize only source-presentation punctuation pairs confirmed by CI."""
    return "".join(PUNCTUATION_EQUIVALENTS.get(char, char) for char in value)


def classify_surface_alignment(sbl_surface: str, morph_surface: str) -> str:
    """Classify a source-token pair or fail on a lexical/unsupported punctuation mismatch."""
    if sbl_surface == morph_surface:
        return "exact"
    if strip_apparatus_markers(sbl_surface) == strip_apparatus_markers(morph_surface):
        return "apparatus-normalized"
    if normalize_punctuation(sbl_surface) == normalize_punctuation(morph_surface):
        return "punctuation-normalized"
    sbl_combined = normalize_punctuation(strip_apparatus_markers(sbl_surface))
    morph_combined = normalize_punctuation(strip_apparatus_markers(morph_surface))
    if sbl_combined == morph_combined:
        return "apparatus-punctuation-normalized"
    raise BuildError(
        "surface tokens differ beyond approved source-presentation normalizations: "
        f"SBLGNT={sbl_surface!r}, MorphGNT={morph_surface!r}"
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
        lower = char.lower()
        mapped = GREEK_MAP.get(lower)
        if mapped is None:
            continue
        if not base_seen:
            first_base_upper = char.isupper()
            base_seen = True
        out.append(mapped)
    result = "".join(out)
    if rough and result:
        if result.startswith("r"):
            result = "rh" + result[1:]
        else:
            result = "h" + result
    if first_base_upper and result:
        result = result[0].upper() + result[1:]
    return result


def token_id(book_id: str, chapter: int, verse: int, position: int) -> str:
    return f"{book_id}-{chapter}-{verse}-GR-{position:03d}"


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build_book(book: dict, lock: dict, output: Path) -> dict:
    book_id = str(book["book_id"])
    book_name = str(book["name"])
    sbl_source = lock["sources"]["sblgnt"]
    morph_source = lock["sources"]["morphgnt"]

    sbl_text, sbl_sha256 = download_pinned(
        sbl_source["repository"],
        sbl_source["commit"],
        book["sblgnt"]["path"],
        book["sblgnt"]["blob_sha1"],
    )
    morph_text, morph_sha256 = download_pinned(
        morph_source["repository"],
        morph_source["commit"],
        book["morphgnt"]["path"],
        book["morphgnt"]["blob_sha1"],
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
    token_total = 0
    exact_token_total = 0
    apparatus_token_total = 0
    punctuation_token_total = 0
    combined_token_total = 0
    exact_verse_total = 0
    normalized_verse_total = 0

    for chapter, verse in sorted(sbl_verses):
        text = sbl_verses[(chapter, verse)]
        surfaces = text.split()
        morph_rows = morph_verses[(chapter, verse)]
        if len(surfaces) != len(morph_rows):
            raise BuildError(
                f"{book_name} {chapter}:{verse}: token-count mismatch; "
                f"SBLGNT count={len(surfaces)}, MorphGNT count={len(morph_rows)}"
            )

        surface_tokens = []
        linguistic_tokens = []
        ids = []
        verse_counts = {
            "exact": 0,
            "apparatus-normalized": 0,
            "punctuation-normalized": 0,
            "apparatus-punctuation-normalized": 0,
        }
        for position, (surface, morph_row) in enumerate(zip(surfaces, morph_rows), start=1):
            try:
                alignment_mode = classify_surface_alignment(surface, morph_row["surface"])
            except BuildError as exc:
                raise BuildError(
                    f"{book_name} {chapter}:{verse} token {position}: {exc}"
                ) from exc
            verse_counts[alignment_mode] += 1

            current_id = token_id(book_id, chapter, verse, position)
            ids.append(current_id)
            transliteration = transliterate_greek(surface)
            if not transliteration:
                raise BuildError(f"{book_name} {chapter}:{verse} token {position}: transliteration is empty")
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
        normalized_count = (
            verse_counts["apparatus-normalized"]
            + verse_counts["punctuation-normalized"]
            + verse_counts["apparatus-punctuation-normalized"]
        )
        verse_mode = "exact" if normalized_count == 0 else "source-presentation-normalized"
        alignment_verses.append(
            {
                "chapter": chapter,
                "verse": str(verse),
                "token_count": len(ids),
                "token_ids": ids,
                "alignment_mode": verse_mode,
                "exact_token_count": verse_counts["exact"],
                "apparatus_normalized_token_count": verse_counts["apparatus-normalized"],
                "punctuation_normalized_token_count": verse_counts["punctuation-normalized"],
                "apparatus_punctuation_normalized_token_count": verse_counts[
                    "apparatus-punctuation-normalized"
                ],
                "lexical_mismatch_count": 0,
            }
        )
        token_total += len(ids)
        exact_token_total += verse_counts["exact"]
        apparatus_token_total += verse_counts["apparatus-normalized"]
        punctuation_token_total += verse_counts["punctuation-normalized"]
        combined_token_total += verse_counts["apparatus-punctuation-normalized"]
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
        "apparatus_normalized_token_count": apparatus_token_total,
        "punctuation_normalized_token_count": punctuation_token_total,
        "apparatus_punctuation_normalized_token_count": combined_token_total,
        "exact_verse_count": exact_verse_total,
        "source_presentation_normalized_verse_count": normalized_verse_total,
        "lexical_mismatch_count": 0,
        "alignment_mismatch_count": 0,
        "apparatus_markers_ignored_for_comparison_only": sorted(APPARATUS_MARKERS),
        "punctuation_equivalents_for_comparison_only": PUNCTUATION_EQUIVALENTS,
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
        "apparatus_normalized_token_count": apparatus_token_total,
        "punctuation_normalized_token_count": punctuation_token_total,
        "apparatus_punctuation_normalized_token_count": combined_token_total,
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
    ids = [row.get("book_id") for row in books]
    if len(set(ids)) != 27:
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
    parser.add_argument(
        "--keep-output",
        action="store_true",
        help="Do not remove an existing output directory before generation.",
    )
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
        "apparatus_normalized_token_count": sum(
            row["apparatus_normalized_token_count"] for row in book_stats
        ),
        "punctuation_normalized_token_count": sum(
            row["punctuation_normalized_token_count"] for row in book_stats
        ),
        "apparatus_punctuation_normalized_token_count": sum(
            row["apparatus_punctuation_normalized_token_count"] for row in book_stats
        ),
        "exact_alignment_verse_count": sum(row["exact_verse_count"] for row in book_stats),
        "source_presentation_normalized_verse_count": sum(
            row["source_presentation_normalized_verse_count"] for row in book_stats
        ),
        "lexical_mismatch_count": sum(row["lexical_mismatch_count"] for row in book_stats),
        "alignment_mismatch_count": sum(row["alignment_mismatch_count"] for row in book_stats),
        "alignment_policy": {
            "mode": "exact-or-enumerated-source-presentation-normalizations",
            "apparatus_markers_ignored_for_comparison_only": sorted(APPARATUS_MARKERS),
            "punctuation_equivalents_for_comparison_only": PUNCTUATION_EQUIVALENTS,
            "source_surfaces_preserved": True,
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

    normalized_token_count = (
        manifest["apparatus_normalized_token_count"]
        + manifest["punctuation_normalized_token_count"]
        + manifest["apparatus_punctuation_normalized_token_count"]
    )
    print(
        "[Greek NT Phase 1] generated "
        f"{manifest['book_count']} books, {manifest['chapter_count']} chapters, "
        f"{manifest['verse_count']} verses, {manifest['token_count']} aligned tokens "
        f"({normalized_token_count} source-presentation-normalized); "
        "production remains disabled"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        raise SystemExit(f"Greek NT Phase 1 build failed: {exc}") from exc
