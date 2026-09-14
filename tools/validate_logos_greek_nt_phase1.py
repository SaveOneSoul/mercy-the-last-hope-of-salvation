#!/usr/bin/env python3
"""Validate Greek NT Expansion Phase 1 source locks and generated corpus output."""

from __future__ import annotations

import argparse
import json
import re
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
SBL_COMMIT = "c4d241a9c1c479a55b989ba35a4976c1d0b8052c"
MORPH_COMMIT = "aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d"
JOHN_SBL_BLOB = "a79ae036447d48fd88c4db8e166c771b4fc57d93"
JOHN_MORPH_BLOB = "c3dab42934edab531f7dc08b630be8181638bd61"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> None:
    raise SystemExit(f"Greek NT Phase 1 validation failed: {message}")


def load(path: Path) -> dict:
    if not path.exists():
        fail(f"missing {path.relative_to(ROOT) if path.is_relative_to(ROOT) else path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot parse {path}: {exc}")


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

    for row in books:
        for source_key in ("sblgnt", "morphgnt"):
            part = row.get(source_key) or {}
            if not str(part.get("path") or "").strip():
                fail(f"{row.get('book_id')} missing {source_key} path")
            if not HEX40.fullmatch(str(part.get("blob_sha1") or "")):
                fail(f"{row.get('book_id')} has invalid {source_key} blob SHA-1")
    by_id = {row["book_id"]: row for row in books}
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
        fail("MorphGNT must not become a production source before Phase 1 corpus validation passes")

    profile = (books_payload.get("profiles") or {}).get("greek-nt") or {}
    if profile.get("primary_text_source") != "sblgnt":
        fail("Greek NT profile must use SBLGNT surface text")
    nt_books = [row for row in (books_payload.get("books") or []) if row.get("testament") == "NT"]
    if len(nt_books) != 27 or [row.get("id") for row in nt_books] != EXPECTED_IDS:
        fail("Catholic book registry must expose the same 27 NT books as the Phase 1 source lock")

    if not IMPORTER_PATH.exists():
        fail("Greek NT Phase 1 importer script is missing")
    importer = IMPORTER_PATH.read_text(encoding="utf-8")
    for required in ("git_blob_sha1", "exact_surface_alignment", "production_enabled", "gloss_layer"):
        if required not in importer:
            fail(f"importer is missing required gate marker {required!r}")

    if proto.get("reference") != "John 1:1" or len(proto.get("tokens") or []) != 17:
        fail("accepted prototype record is missing or changed unexpectedly")

    print(
        "Greek NT Phase 1 static validation passed: "
        "owner acceptance, 27 source locks, SBLGNT/MorphGNT pins, and ShareAlike partitions verified"
    )
    return lock


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
    if verse_count < 7900:
        fail(f"generated verse count too small: {verse_count}")
    if token_count < 130000:
        fail(f"generated token count too small: {token_count}")
    if manifest.get("alignment_mismatch_count") != 0:
        fail("generated corpus has alignment mismatches")
    if manifest.get("exact_alignment_verse_count") != verse_count:
        fail("not every generated verse is exactly aligned")
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

    total_alignment_verses = 0
    for book_id in EXPECTED_IDS:
        surface_path = path / "surface" / f"{book_id}.json"
        ling_path = path / "linguistics" / f"{book_id}.json"
        align_path = path / "alignment" / f"{book_id}.json"
        surface = load(surface_path)
        ling = load(ling_path)
        align = load(align_path)
        if surface.get("layer") != "surface" or ling.get("layer") != "linguistics":
            fail(f"{book_id}: generated layer labels are invalid")
        if surface.get("source", {}).get("blob_sha1") != lock_by_id[book_id]["sblgnt"]["blob_sha1"]:
            fail(f"{book_id}: SBLGNT blob lock mismatch in generated output")
        if ling.get("source", {}).get("blob_sha1") != lock_by_id[book_id]["morphgnt"]["blob_sha1"]:
            fail(f"{book_id}: MorphGNT blob lock mismatch in generated output")
        if not HEX64.fullmatch(str(surface.get("source", {}).get("sha256") or "")):
            fail(f"{book_id}: surface SHA-256 missing")
        if not HEX64.fullmatch(str(ling.get("source", {}).get("sha256") or "")):
            fail(f"{book_id}: linguistic SHA-256 missing")
        if ling.get("source", {}).get("license") != "CC BY-SA 3.0":
            fail(f"{book_id}: linguistic ShareAlike licence missing")
        if align.get("contains_source_text") is not False or align.get("contains_linguistic_payload") is not False:
            fail(f"{book_id}: alignment layer leaked source payload")
        verses = align.get("verses") or []
        if align.get("alignment_mismatch_count") != 0:
            fail(f"{book_id}: alignment mismatch count is non-zero")
        for verse in verses:
            if verse.get("exact_surface_alignment") is not True:
                fail(f"{book_id}: non-exact alignment record detected")
            ids = verse.get("token_ids") or []
            if verse.get("token_count") != len(ids):
                fail(f"{book_id}: token count/id list mismatch")
        total_alignment_verses += len(verses)

        serialized_surface = json.dumps(surface, ensure_ascii=False)
        serialized_ling = json.dumps(ling, ensure_ascii=False)
        if '"gloss"' in serialized_surface or '"gloss"' in serialized_ling:
            fail(f"{book_id}: Phase 1 generated output must not invent glosses")

    if total_alignment_verses != verse_count:
        fail("sum of per-book alignment verses differs from manifest verse count")

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
    if len(surface_tokens) != 17 or len(ling_tokens) != 17:
        fail("generated John 1:1 token count differs from accepted prototype")
    for index, (surface_row, ling_row, proto_row) in enumerate(
        zip(surface_tokens, ling_tokens, proto_tokens), start=1
    ):
        if surface_row.get("surface") != proto_row.get("surface"):
            fail(f"John 1:1 token {index}: surface mismatch")
        if ling_row.get("lemma") != proto_row.get("lemma"):
            fail(f"John 1:1 token {index}: lemma mismatch")
        if ling_row.get("morphology") != proto_row.get("morphology"):
            fail(f"John 1:1 token {index}: morphology mismatch")
        if surface_row.get("id") != ling_row.get("id"):
            fail(f"John 1:1 token {index}: partition token id mismatch")
        if not surface_row.get("transliteration"):
            fail(f"John 1:1 token {index}: derived transliteration missing")

    print(
        "Greek NT Phase 1 generated-corpus validation passed: "
        f"27 books, {manifest['chapter_count']} chapters, {verse_count} verses, "
        f"{token_count} exact-aligned tokens, production disabled"
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--generated", type=Path, help="Validate a generated Phase 1 output directory")
    args = parser.parse_args()
    lock = validate_static()
    if args.generated:
        validate_generated(args.generated.resolve(), lock)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
