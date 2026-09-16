#!/usr/bin/env python3
"""Validate Greek NT Expansion Phase 1 source locks and generated corpus output."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "cloud-backend" / "app" / "logos_interlinear"
LOCK_PATH = BASE / "greek_nt_phase1" / "source-lock.json"
PROTO_PATH = BASE / "prototypes" / "john-1-1" / "JHN-1-1.json"
PROTO_SOURCES_PATH = BASE / "prototypes" / "john-1-1" / "sources-manifest.json"
GLOBAL_SOURCES_PATH = BASE / "sources-manifest.json"
BOOKS_PATH = BASE / "books.json"
IMPORTER_PATH = ROOT / "scripts" / "vendor_greek_nt_phase1.py"

EXPECTED_IDS = [
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL",
    "EPH", "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM",
    "HEB", "JAS", "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV",
]
EXPECTED_JOHN_MORPH_GAPS = {
    "7:53", "8:1", "8:2", "8:3", "8:4", "8:5", "8:6",
    "8:7", "8:8", "8:9", "8:10", "8:11",
}
SBL_COMMIT = "c4d241a9c1c479a55b989ba35a4976c1d0b8052c"
MORPH_COMMIT = "aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d"
JOHN_SBL_BLOB = "a79ae036447d48fd88c4db8e166c771b4fc57d93"
JOHN_MORPH_BLOB = "c3dab42934edab531f7dc08b630be8181638bd61"
APPARATUS_MARKERS = frozenset({"⸀", "⸂", "⸃"})
ELISION_MARKERS = frozenset({"ʼ", "’"})
SHORT_REF_RE = re.compile(r"^(\d+):(\d+)$")
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


class ValidationError(RuntimeError):
    pass


def fail(message: str) -> None:
    raise ValidationError(message)


def load(path: Path) -> dict:
    if not path.exists():
        fail(f"missing {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot parse {path}: {exc}")


def parse_short_refs(values: list[str], label: str) -> set[tuple[int, int]]:
    parsed: set[tuple[int, int]] = set()
    for raw in values:
        match = SHORT_REF_RE.fullmatch(str(raw))
        if not match:
            fail(f"{label}: malformed verse reference {raw!r}")
        key = (int(match.group(1)), int(match.group(2)))
        if key in parsed:
            fail(f"{label}: duplicate verse reference {raw!r}")
        parsed.add(key)
    return parsed


def ref_string(key: tuple[int, int]) -> str:
    return f"{key[0]}:{key[1]}"


def lock_gap_refs(book: dict) -> set[tuple[int, int]]:
    morph = book.get("morphgnt") or {}
    refs = parse_short_refs(list(morph.get("expected_missing_verses") or []), f"{book.get('book_id')} gap lock")
    if refs and not str(morph.get("missing_reason") or "").strip():
        fail(f"{book.get('book_id')}: source-locked annotation gaps require a missing_reason")
    return refs


def lexical_alignment_key(value: str) -> str:
    """Mirror the importer's comparison-only lexical-core normalization."""
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


def expected_alignment_mode(sbl_surface: str, morph_surface: str) -> str | None:
    if sbl_surface == morph_surface:
        return "exact"
    sbl_key = lexical_alignment_key(sbl_surface)
    morph_key = lexical_alignment_key(morph_surface)
    if sbl_key and sbl_key == morph_key:
        return "source-presentation-normalized"
    return None


def validate_static() -> dict:
    lock = load(LOCK_PATH)
    proto = load(PROTO_PATH)
    proto_sources = load(PROTO_SOURCES_PATH)
    global_sources = load(GLOBAL_SOURCES_PATH)
    books_payload = load(BOOKS_PATH)

    if lock.get("phase") != "Greek NT Expansion Phase 1":
        fail("source lock has unexpected phase")
    if lock.get("status") != "validation-only":
        fail("Phase 1 source lock must remain validation-only")
    if lock.get("production", {}).get("enabled") is not False:
        fail("Phase 1 must not enable production")

    acceptance = lock.get("owner_acceptance") or {}
    if acceptance.get("accepted") is not True or acceptance.get("prototype_pr") != 6:
        fail("owner acceptance of the John 1:1 prototype is not recorded")
    if acceptance.get("prototype_merge_commit") != "4a00a0afb5a578b3c7cb3e737cdd12348c52e821":
        fail("prototype merge commit in owner acceptance record changed")

    sbl = lock.get("sources", {}).get("sblgnt") or {}
    morph = lock.get("sources", {}).get("morphgnt") or {}
    if sbl.get("repository") != "Faithlife/SBLGNT" or sbl.get("commit") != SBL_COMMIT:
        fail("SBLGNT source pin changed")
    if sbl.get("license") != "CC BY 4.0":
        fail("SBLGNT licence must remain CC BY 4.0")
    if morph.get("repository") != "morphgnt/sblgnt" or morph.get("commit") != MORPH_COMMIT:
        fail("MorphGNT source pin changed")
    if "CC BY-SA 3.0" not in str(morph.get("license")):
        fail("MorphGNT annotation licence must remain CC BY-SA 3.0")
    if morph.get("share_alike") is not True or morph.get("isolation_required") is not True:
        fail("MorphGNT ShareAlike partition is not enforced")

    partitions = lock.get("license_partitions") or {}
    if set(partitions) != {"surface", "linguistics", "alignment"}:
        fail("expected surface, linguistics and alignment licence partitions")
    subdirs = [partitions[name].get("output_subdir") for name in partitions]
    if len(set(subdirs)) != 3:
        fail("licence partitions must use distinct output directories")
    if partitions["surface"].get("license") != "CC BY 4.0":
        fail("surface partition licence mismatch")
    if partitions["linguistics"].get("license") != "CC BY-SA 3.0":
        fail("linguistics partition licence mismatch")
    if partitions["linguistics"].get("share_alike") is not True:
        fail("linguistics partition must retain ShareAlike")
    if partitions["alignment"].get("contains_source_text") is not False:
        fail("alignment partition must not contain source text")

    books = lock.get("books") or []
    if len(books) != 27:
        fail(f"expected 27 source-locked books, found {len(books)}")
    if [row.get("order") for row in books] != list(range(1, 28)):
        fail("source-lock order must be exactly 1..27")
    ids = [row.get("book_id") for row in books]
    if ids != EXPECTED_IDS:
        fail("source-lock NT book order/id mapping changed")
    if len({row.get("name") for row in books}) != 27:
        fail("source-lock book names are not unique")

    by_id = {row["book_id"]: row for row in books}
    for row in books:
        for source_key in ("sblgnt", "morphgnt"):
            part = row.get(source_key) or {}
            if not str(part.get("path") or "").strip():
                fail(f"{row.get('book_id')} missing {source_key} path")
            if not HEX40.fullmatch(str(part.get("blob_sha1") or "")):
                fail(f"{row.get('book_id')} has invalid {source_key} blob SHA-1")

        gaps = {ref_string(key) for key in lock_gap_refs(row)}
        if row.get("book_id") == "JHN":
            if gaps != EXPECTED_JOHN_MORPH_GAPS:
                fail(
                    "John MorphGNT gap lock must be exactly John 7:53-8:11; "
                    f"found {sorted(gaps)}"
                )
        elif gaps:
            fail(f"{row.get('book_id')}: unexpected MorphGNT annotation-gap lock {sorted(gaps)}")

    if by_id["JHN"]["sblgnt"]["blob_sha1"] != JOHN_SBL_BLOB:
        fail("John SBLGNT blob no longer matches accepted prototype")
    if by_id["JHN"]["morphgnt"]["blob_sha1"] != JOHN_MORPH_BLOB:
        fail("John MorphGNT blob no longer matches accepted prototype")

    proto_index = {row["id"]: row for row in proto_sources.get("sources") or []}
    if proto_index.get("sblgnt", {}).get("commit") != SBL_COMMIT:
        fail("prototype SBLGNT commit differs from Phase 1")
    if proto_index.get("morphgnt-sblgnt", {}).get("commit") != MORPH_COMMIT:
        fail("prototype MorphGNT commit differs from Phase 1")

    global_index = {row["id"]: row for row in global_sources.get("sources") or []}
    global_sbl = global_index.get("sblgnt") or {}
    if global_sbl.get("pin", {}).get("value") != SBL_COMMIT:
        fail("global SBLGNT source registry pin differs from Phase 1")
    if "morphgnt-sblgnt" in global_index and global_index["morphgnt-sblgnt"].get("production_import_allowed") is not False:
        fail("MorphGNT must not become a production source before Phase 1 validation passes")

    profile = (books_payload.get("profiles") or {}).get("greek-nt") or {}
    if profile.get("primary_text_source") != "sblgnt":
        fail("Greek NT profile must use SBLGNT surface text")
    nt_books = [row for row in (books_payload.get("books") or []) if row.get("testament") == "NT"]
    if len(nt_books) != 27 or [row.get("id") for row in nt_books] != EXPECTED_IDS:
        fail("Catholic book registry must expose the same 27 NT books as the Phase 1 source lock")

    if not IMPORTER_PATH.exists():
        fail("Greek NT Phase 1 importer script is missing")
    importer = IMPORTER_PATH.read_text(encoding="utf-8")
    for required in (
        "git_blob_sha1",
        "APPARATUS_MARKERS",
        "ELISION_MARKERS",
        "casefolded_for_comparison",
        "expected_missing_verses",
        "surface-only-annotation-gap",
        "annotation_gap_token_count",
        "annotation_gap_verse_count",
        "fabricate_morphology",
        "lexical_alignment_key",
        "classify_surface_alignment",
        "source_presentation_normalized_token_count",
        "lexical_mismatch_count",
        "production_enabled",
        "gloss_layer",
    ):
        if required not in importer:
            fail(f"importer is missing required gate marker {required!r}")

    if proto.get("reference") != "John 1:1" or len(proto.get("tokens") or []) != 17:
        fail("accepted prototype record is missing or changed unexpectedly")

    print(
        "Greek NT Phase 1 static validation passed: owner acceptance, 27 source locks, "
        "SBLGNT/MorphGNT pins, ShareAlike partitions, lexical-core alignment, and "
        "the source-locked John 7:53-8:11 MorphGNT annotation gap verified"
    )
    return lock


def validate_policy(policy: dict, label: str) -> None:
    if policy.get("unicode_normalization") != "NFC":
        fail(f"{label}: Unicode normalization changed")
    if policy.get("casefolded_for_comparison") is not True:
        fail(f"{label}: casefold comparison rule changed")
    if policy.get("ignored_apparatus_markers") != sorted(APPARATUS_MARKERS):
        fail(f"{label}: apparatus marker set changed")
    if policy.get("ignored_elision_markers") != sorted(ELISION_MARKERS):
        fail(f"{label}: elision marker set changed")
    if policy.get("ignored_unicode_categories") != ["P*"]:
        fail(f"{label}: punctuation-category rule changed")
    if policy.get("preserved_for_comparison") != ["Greek letters", "combining marks"]:
        fail(f"{label}: preserved-character rule changed")
    if policy.get("source_surfaces_preserved") is not True:
        fail(f"{label}: source surfaces must remain preserved")


def validate_generated(path: Path, lock: dict) -> None:
    manifest = load(path / "manifest.json")
    if manifest.get("phase") != lock.get("phase"):
        fail("generated manifest phase mismatch")
    if manifest.get("status") != "validation-generated":
        fail("generated manifest must remain validation-generated")
    if manifest.get("production_enabled") is not False:
        fail("generated Greek NT corpus must not be marked production-enabled")
    if manifest.get("book_count") != 27:
        fail(f"generated book count is {manifest.get('book_count')}, expected 27")
    if manifest.get("chapter_count") != 260:
        fail(f"generated chapter count is {manifest.get('chapter_count')}, expected 260")

    verse_count = int(manifest.get("verse_count") or 0)
    token_count = int(manifest.get("token_count") or 0)
    exact_token_count = int(manifest.get("exact_token_count") or 0)
    normalized_token_count = int(manifest.get("source_presentation_normalized_token_count") or 0)
    gap_token_count = int(manifest.get("annotation_gap_token_count") or 0)
    exact_verse_count = int(manifest.get("exact_alignment_verse_count") or 0)
    normalized_verse_count = int(manifest.get("source_presentation_normalized_verse_count") or 0)
    gap_verse_count = int(manifest.get("annotation_gap_verse_count") or 0)
    morphology_coverage_verse_count = int(manifest.get("morphology_coverage_verse_count") or 0)

    if verse_count < 7900:
        fail(f"generated verse count too small: {verse_count}")
    if token_count < 130000:
        fail(f"generated token count too small: {token_count}")
    if exact_token_count + normalized_token_count + gap_token_count != token_count:
        fail("manifest exact/normalized/gap token counts do not sum to total token count")
    if exact_verse_count + normalized_verse_count + gap_verse_count != verse_count:
        fail("manifest exact/normalized/gap verse counts do not sum to verse count")
    if morphology_coverage_verse_count + gap_verse_count != verse_count:
        fail("manifest MorphGNT coverage plus annotation gaps does not sum to verse count")
    if gap_verse_count != len(EXPECTED_JOHN_MORPH_GAPS):
        fail(f"generated annotation-gap verse count is {gap_verse_count}, expected 12")
    if manifest.get("lexical_mismatch_count") != 0 or manifest.get("alignment_mismatch_count") != 0:
        fail("generated corpus has lexical/alignment mismatches")

    policy = manifest.get("alignment_policy") or {}
    if policy.get("mode") != "exact-or-lexical-core-with-source-presentation-ignored":
        fail("generated alignment policy mode changed")
    validate_policy(policy, "manifest alignment policy")

    gap_policy = manifest.get("annotation_gap_policy") or {}
    if gap_policy.get("mode") != "source-locked-only":
        fail("annotation-gap policy must remain source-locked-only")
    if gap_policy.get("fabricate_morphology") is not False:
        fail("annotation-gap policy must forbid fabricated morphology")
    if gap_policy.get("surface_text_preserved") is not True:
        fail("annotation-gap policy must preserve SBLGNT surface text")

    if manifest.get("source_commits", {}).get("sblgnt") != SBL_COMMIT:
        fail("generated manifest SBLGNT commit mismatch")
    if manifest.get("source_commits", {}).get("morphgnt") != MORPH_COMMIT:
        fail("generated manifest MorphGNT commit mismatch")
    if manifest.get("gloss_layer", {}).get("installed") is not False:
        fail("Phase 1 must not claim an installed gloss layer")

    book_rows = manifest.get("books") or []
    if [row.get("book_id") for row in book_rows] != EXPECTED_IDS:
        fail("generated book order differs from source lock")
    lock_by_id = {row["book_id"]: row for row in lock["books"]}
    manifest_by_id = {row["book_id"]: row for row in book_rows}

    observed_exact_tokens = 0
    observed_normalized_tokens = 0
    observed_gap_tokens = 0
    observed_exact_verses = 0
    observed_normalized_verses = 0
    observed_gap_verses = 0
    total_alignment_verses = 0

    for book_id in EXPECTED_IDS:
        lock_book = lock_by_id[book_id]
        expected_gaps = lock_gap_refs(lock_book)
        surface = load(path / "surface" / f"{book_id}.json")
        ling = load(path / "linguistics" / f"{book_id}.json")
        align = load(path / "alignment" / f"{book_id}.json")
        manifest_book = manifest_by_id[book_id]

        if surface.get("layer") != "surface" or ling.get("layer") != "linguistics" or align.get("layer") != "alignment":
            fail(f"{book_id}: generated layer labels are invalid")
        if surface.get("source", {}).get("blob_sha1") != lock_book["sblgnt"]["blob_sha1"]:
            fail(f"{book_id}: SBLGNT blob lock mismatch in generated output")
        if ling.get("source", {}).get("blob_sha1") != lock_book["morphgnt"]["blob_sha1"]:
            fail(f"{book_id}: MorphGNT blob lock mismatch in generated output")
        if not HEX64.fullmatch(str(surface.get("source", {}).get("sha256") or "")):
            fail(f"{book_id}: surface SHA-256 missing")
        if not HEX64.fullmatch(str(ling.get("source", {}).get("sha256") or "")):
            fail(f"{book_id}: linguistic SHA-256 missing")
        if ling.get("source", {}).get("license") != "CC BY-SA 3.0":
            fail(f"{book_id}: linguistic ShareAlike licence missing")
        if ling.get("source", {}).get("share_alike") is not True:
            fail(f"{book_id}: linguistic ShareAlike flag missing")
        if align.get("contains_source_text") is not False or align.get("contains_linguistic_payload") is not False:
            fail(f"{book_id}: alignment layer leaked source payload")
        if align.get("lexical_mismatch_count") != 0 or align.get("alignment_mismatch_count") != 0:
            fail(f"{book_id}: lexical/alignment mismatch count is non-zero")
        validate_policy(align.get("comparison_policy") or {}, f"{book_id} comparison policy")

        generated_gap_refs = parse_short_refs(
            list(ling.get("expected_missing_verses") or []),
            f"{book_id} generated gap registry",
        )
        if generated_gap_refs != expected_gaps:
            fail(f"{book_id}: generated linguistic gap registry differs from source lock")

        verses = align.get("verses") or []
        align_by_ref = {(int(row["chapter"]), str(row["verse"])): row for row in verses}
        if len(align_by_ref) != len(verses):
            fail(f"{book_id}: duplicate alignment verse references")

        book_exact_tokens = 0
        book_normalized_tokens = 0
        book_gap_tokens = 0
        book_exact_verses = 0
        book_normalized_verses = 0
        book_gap_verses = 0
        seen_gap_refs: set[tuple[int, int]] = set()

        surface_chapters = surface.get("chapters") or {}
        linguistic_chapters = ling.get("chapters") or {}
        for chapter_text, surface_verses in surface_chapters.items():
            ling_verses = linguistic_chapters.get(chapter_text) or {}
            for verse_text, surface_verse in surface_verses.items():
                key = (int(chapter_text), int(verse_text))
                ling_verse = ling_verses.get(verse_text)
                if ling_verse is None:
                    fail(f"{book_id} {chapter_text}:{verse_text}: missing linguistic verse record")
                align_verse = align_by_ref.get((int(chapter_text), str(verse_text)))
                if align_verse is None:
                    fail(f"{book_id} {chapter_text}:{verse_text}: missing alignment verse")

                surface_tokens = surface_verse.get("tokens") or []
                ids = align_verse.get("token_ids") or []
                if align_verse.get("token_count") != len(ids) or len(ids) != len(surface_tokens):
                    fail(f"{book_id} {chapter_text}:{verse_text}: surface/alignment token-count mismatch")
                for index, surface_row in enumerate(surface_tokens, start=1):
                    if surface_row.get("id") != ids[index - 1]:
                        fail(f"{book_id} {chapter_text}:{verse_text} token {index}: surface/alignment token id mismatch")
                    if not surface_row.get("transliteration"):
                        fail(f"{book_id} {chapter_text}:{verse_text} token {index}: transliteration missing")

                if key in expected_gaps:
                    seen_gap_refs.add(key)
                    if ling_verse.get("annotation_status") != "unavailable-in-pinned-morphgnt":
                        fail(f"{book_id} {chapter_text}:{verse_text}: expected MorphGNT gap status missing")
                    if (ling_verse.get("tokens") or []) != []:
                        fail(f"{book_id} {chapter_text}:{verse_text}: MorphGNT gap must not contain fabricated tokens")
                    if not str(ling_verse.get("reason") or "").strip():
                        fail(f"{book_id} {chapter_text}:{verse_text}: MorphGNT gap reason missing")
                    if align_verse.get("alignment_mode") != "surface-only-annotation-gap":
                        fail(f"{book_id} {chapter_text}:{verse_text}: annotation-gap alignment mode missing")
                    if int(align_verse.get("exact_token_count") or 0) != 0:
                        fail(f"{book_id} {chapter_text}:{verse_text}: gap verse cannot claim exact MorphGNT tokens")
                    if int(align_verse.get("source_presentation_normalized_token_count") or 0) != 0:
                        fail(f"{book_id} {chapter_text}:{verse_text}: gap verse cannot claim normalized MorphGNT tokens")
                    if int(align_verse.get("annotation_gap_token_count") or 0) != len(surface_tokens):
                        fail(f"{book_id} {chapter_text}:{verse_text}: gap token count mismatch")
                    if int(align_verse.get("lexical_mismatch_count") or 0) != 0:
                        fail(f"{book_id} {chapter_text}:{verse_text}: gap verse cannot claim lexical mismatch")
                    book_gap_tokens += len(surface_tokens)
                    book_gap_verses += 1
                    continue

                if ling_verse.get("annotation_status") != "available":
                    fail(f"{book_id} {chapter_text}:{verse_text}: annotated verse missing available status")
                ling_tokens = ling_verse.get("tokens") or []
                if len(surface_tokens) != len(ling_tokens):
                    fail(f"{book_id} {chapter_text}:{verse_text}: partition token-count mismatch")
                if int(align_verse.get("annotation_gap_token_count") or 0) != 0:
                    fail(f"{book_id} {chapter_text}:{verse_text}: non-gap verse reports annotation-gap tokens")

                verse_exact = 0
                verse_normalized = 0
                for index, (surface_row, ling_row) in enumerate(zip(surface_tokens, ling_tokens), start=1):
                    if surface_row.get("id") != ling_row.get("id") or surface_row.get("id") != ids[index - 1]:
                        fail(f"{book_id} {chapter_text}:{verse_text} token {index}: token id mismatch")
                    sbl_surface = str(surface_row.get("surface") or "")
                    morph_surface = str(ling_row.get("source_surface") or "")
                    expected_mode = expected_alignment_mode(sbl_surface, morph_surface)
                    actual_mode = ling_row.get("alignment_mode")
                    if expected_mode is None:
                        fail(
                            f"{book_id} {chapter_text}:{verse_text} token {index}: "
                            "source surfaces differ lexically after presentation-only normalization"
                        )
                    if actual_mode != expected_mode:
                        fail(
                            f"{book_id} {chapter_text}:{verse_text} token {index}: "
                            f"alignment mode {actual_mode!r} should be {expected_mode!r}"
                        )
                    if actual_mode == "exact":
                        verse_exact += 1
                    else:
                        verse_normalized += 1

                if int(align_verse.get("exact_token_count") or 0) != verse_exact:
                    fail(f"{book_id} {chapter_text}:{verse_text}: exact-token count mismatch")
                if int(align_verse.get("source_presentation_normalized_token_count") or 0) != verse_normalized:
                    fail(f"{book_id} {chapter_text}:{verse_text}: normalized-token count mismatch")
                if int(align_verse.get("lexical_mismatch_count") or 0) != 0:
                    fail(f"{book_id} {chapter_text}:{verse_text}: lexical mismatch recorded")

                expected_verse_mode = "exact" if verse_normalized == 0 else "source-presentation-normalized"
                if align_verse.get("alignment_mode") != expected_verse_mode:
                    fail(f"{book_id} {chapter_text}:{verse_text}: verse alignment mode mismatch")

                book_exact_tokens += verse_exact
                book_normalized_tokens += verse_normalized
                if expected_verse_mode == "exact":
                    book_exact_verses += 1
                else:
                    book_normalized_verses += 1

        if seen_gap_refs != expected_gaps:
            missing = sorted(ref_string(key) for key in (expected_gaps - seen_gap_refs))
            extra = sorted(ref_string(key) for key in (seen_gap_refs - expected_gaps))
            fail(f"{book_id}: generated annotation-gap coverage mismatch; missing={missing}, extra={extra}")

        if book_exact_tokens + book_normalized_tokens + book_gap_tokens != int(align.get("token_count") or 0):
            fail(f"{book_id}: token aggregates differ from alignment token count")
        if book_exact_tokens != int(align.get("exact_token_count") or 0):
            fail(f"{book_id}: exact token aggregate mismatch")
        if book_normalized_tokens != int(align.get("source_presentation_normalized_token_count") or 0):
            fail(f"{book_id}: normalized token aggregate mismatch")
        if book_gap_tokens != int(align.get("annotation_gap_token_count") or 0):
            fail(f"{book_id}: annotation-gap token aggregate mismatch")
        if book_exact_verses != int(align.get("exact_verse_count") or 0):
            fail(f"{book_id}: exact verse aggregate mismatch")
        if book_normalized_verses != int(align.get("source_presentation_normalized_verse_count") or 0):
            fail(f"{book_id}: normalized verse aggregate mismatch")
        if book_gap_verses != int(align.get("annotation_gap_verse_count") or 0):
            fail(f"{book_id}: annotation-gap verse aggregate mismatch")
        if book_exact_verses + book_normalized_verses + book_gap_verses != int(align.get("verse_count") or 0):
            fail(f"{book_id}: alignment verse aggregate mismatch")
        if book_exact_verses + book_normalized_verses != int(align.get("morphology_coverage_verse_count") or 0):
            fail(f"{book_id}: MorphGNT coverage verse aggregate mismatch")

        for field, expected in (
            ("token_count", int(align.get("token_count") or 0)),
            ("exact_token_count", book_exact_tokens),
            ("source_presentation_normalized_token_count", book_normalized_tokens),
            ("annotation_gap_token_count", book_gap_tokens),
            ("exact_verse_count", book_exact_verses),
            ("source_presentation_normalized_verse_count", book_normalized_verses),
            ("annotation_gap_verse_count", book_gap_verses),
            ("morphology_coverage_verse_count", book_exact_verses + book_normalized_verses),
        ):
            if int(manifest_book.get(field) or 0) != expected:
                fail(f"{book_id}: manifest book field {field} does not match generated alignment")

        observed_exact_tokens += book_exact_tokens
        observed_normalized_tokens += book_normalized_tokens
        observed_gap_tokens += book_gap_tokens
        observed_exact_verses += book_exact_verses
        observed_normalized_verses += book_normalized_verses
        observed_gap_verses += book_gap_verses
        total_alignment_verses += len(verses)

        serialized_surface = json.dumps(surface, ensure_ascii=False)
        serialized_ling = json.dumps(ling, ensure_ascii=False)
        if '"gloss"' in serialized_surface or '"gloss"' in serialized_ling:
            fail(f"{book_id}: Phase 1 generated output must not invent glosses")

    if total_alignment_verses != verse_count:
        fail("sum of per-book alignment verses differs from manifest verse count")
    if observed_exact_tokens != exact_token_count:
        fail("observed exact token total differs from manifest")
    if observed_normalized_tokens != normalized_token_count:
        fail("observed normalized token total differs from manifest")
    if observed_gap_tokens != gap_token_count:
        fail("observed annotation-gap token total differs from manifest")
    if observed_exact_verses != exact_verse_count:
        fail("observed exact verse total differs from manifest")
    if observed_normalized_verses != normalized_verse_count:
        fail("observed normalized verse total differs from manifest")
    if observed_gap_verses != gap_verse_count:
        fail("observed annotation-gap verse total differs from manifest")

    john_surface = load(path / "surface" / "JHN.json")
    john_ling = load(path / "linguistics" / "JHN.json")
    proto = load(PROTO_PATH)
    surface_verse = john_surface["chapters"]["1"]["1"]
    ling_verse = john_ling["chapters"]["1"]["1"]
    if surface_verse.get("text") != proto.get("greek_text"):
        fail("generated John 1:1 surface differs from accepted prototype")
    surface_tokens = surface_verse.get("tokens") or []
    ling_tokens = ling_verse.get("tokens") or []
    proto_tokens = proto.get("tokens") or []
    if ling_verse.get("annotation_status") != "available":
        fail("generated John 1:1 must remain morphologically annotated")
    if len(surface_tokens) != 17 or len(ling_tokens) != 17:
        fail("generated John 1:1 token count differs from accepted prototype")
    for index, (surface_row, ling_row, proto_row) in enumerate(zip(surface_tokens, ling_tokens, proto_tokens), start=1):
        if surface_row.get("surface") != proto_row.get("surface"):
            fail(f"John 1:1 token {index}: surface mismatch")
        if ling_row.get("lemma") != proto_row.get("lemma"):
            fail(f"John 1:1 token {index}: lemma mismatch")
        if ling_row.get("morphology") != proto_row.get("morphology"):
            fail(f"John 1:1 token {index}: morphology mismatch")
        if surface_row.get("id") != ling_row.get("id"):
            fail(f"John 1:1 token {index}: partition token id mismatch")
        if ling_row.get("alignment_mode") != "exact":
            fail(f"John 1:1 token {index}: accepted prototype should remain exact-aligned")
        if not surface_row.get("transliteration"):
            fail(f"John 1:1 token {index}: derived transliteration missing")

    print(
        "Greek NT Phase 1 generated-corpus validation passed: "
        f"27 books, {manifest['chapter_count']} chapters, {verse_count} verses, "
        f"{token_count} SBLGNT surface tokens, {morphology_coverage_verse_count} verses with MorphGNT annotations, "
        f"{gap_verse_count} source-locked annotation-gap verses, zero lexical mismatches, production disabled"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", type=Path, help="Validate a generated Phase 1 output directory")
    args = parser.parse_args()
    try:
        lock = validate_static()
        if args.generated:
            validate_generated(args.generated.resolve(), lock)
    except ValidationError as exc:
        raise SystemExit(f"Greek NT Phase 1 validation failed: {exc}") from exc
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
