#!/usr/bin/env python3
"""Validate the production Swete protocanonical OT expansion."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_ot_swete_protocanonical"
EXPECTED_SOURCE_COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
EXPECTED_TREE = "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79"
EXPECTED_BOOKS = {
    "GEN","EXO","LEV","NUM","DEU","JOS","JDG","RUT","1SA","2SA","1KI","2KI","1CH","2CH",
    "EZR","NEH","JOB","PSA","PRO","ECC","SNG","ISA","JER","LAM","EZK","HOS","JOL","AMO",
    "OBA","JON","MIC","NAM","HAB","ZEP","HAG","ZEC","MAL"
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def fail(message: str) -> None:
    raise SystemExit(f"OT Septuagint validation failed: {message}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.exists():
        fail("manifest missing")
    manifest = load(manifest_path)

    if manifest.get("corpus_id") != "grc_ot_swete_protocanonical": fail("wrong corpus id")
    if manifest.get("production_enabled") is not True: fail("production must be enabled")
    if int(manifest.get("book_count") or 0) != 37: fail("expected 37 books")
    if set(manifest.get("supported_canonical_books") or []) != EXPECTED_BOOKS: fail("supported-book set changed")
    if int(manifest.get("chapter_count") or 0) < 850: fail("unexpectedly low chapter count")
    if int(manifest.get("verse_count") or 0) < 20000: fail("unexpectedly low verse count")

    source = manifest.get("source") or {}
    if source.get("repository") != "OpenGreekAndLatin/First1KGreek": fail("wrong source repository")
    if source.get("commit") != EXPECTED_SOURCE_COMMIT: fail("source commit changed")
    if source.get("septuagint_tree_sha") != EXPECTED_TREE: fail("source tree changed")
    if source.get("license") != "CC BY-SA 4.0": fail("license changed")
    if source.get("share_alike") is not True or source.get("isolation_required") is not True: fail("ShareAlike boundary changed")

    layers = manifest.get("derived_layers") or {}
    if any(layers.get(k) is not False for k in ("glosses","lemmata","morphology","transliteration")):
        fail("unapproved derived layer enabled")
    vers = manifest.get("versification") or {}
    if vers.get("runtime_exact_identity_required") is not True or vers.get("automatic_remapping") is not False:
        fail("versification safety gate changed")
    if vers.get("fabricate_verse_boundaries") is not False:
        fail("verse fabrication must remain disabled")
    if vers.get("empty_source_loci_are_not_filled_from_neighboring_text") is not True:
        fail("empty-source-locus safety contract missing")
    serving = manifest.get("serving_contract") or {}
    if serving.get("no_fabricated_source_surface_for_empty_tei_loci") is not True:
        fail("source-gap fabrication guard missing")

    books_root = root / "sharealike" / "first1kgreek_swete_cc-by-sa-4.0" / "books"
    if not books_root.is_dir(): fail("isolated book partition missing")
    actual_files = {p.stem for p in books_root.glob("*.json")}
    if actual_files != EXPECTED_BOOKS: fail("book files do not match supported set")

    counted_chapters = 0
    counted_verses = 0
    counted_gaps = 0
    for book_id in sorted(EXPECTED_BOOKS):
        payload = load(books_root / f"{book_id}.json")
        if payload.get("book_id") != book_id: fail(f"{book_id}: identity mismatch")
        if payload.get("production_enabled") is not True: fail(f"{book_id}: production disabled")
        src = payload.get("source") or {}
        if src.get("license") != "CC BY-SA 4.0" or src.get("share_alike") is not True: fail(f"{book_id}: rights mismatch")
        if not src.get("git_blob_sha1") or not src.get("sha256"): fail(f"{book_id}: immutable source digests missing")
        gaps = payload.get("empty_source_loci_not_auto_served") or []
        for gap in gaps:
            if gap.get("reason") != "empty_source_tei_verse_div": fail(f"{book_id}: unexpected source-gap reason")
            if gap.get("fabricated_surface") is not False: fail(f"{book_id}: source gap was fabricated")
            if not gap.get("source_reference"): fail(f"{book_id}: source-gap reference missing")
            counted_gaps += 1
        chapters = payload.get("chapters") or {}
        if not chapters: fail(f"{book_id}: no chapters")
        counted_chapters += len(chapters)
        for chapter, verses in chapters.items():
            if not str(chapter).isdigit() or not verses: fail(f"{book_id}: invalid canonical chapter")
            for verse, row in verses.items():
                if not str(verse).isdigit(): fail(f"{book_id} {chapter}: nonnumeric auto-served verse")
                if not str(row.get("surface") or "").strip(): fail(f"{book_id} {chapter}:{verse}: empty Greek surface")
                if not str(row.get("source_reference") or "").strip(): fail(f"{book_id} {chapter}:{verse}: missing source reference")
                counted_verses += 1

    if counted_chapters != int(manifest["chapter_count"]): fail("chapter total mismatch")
    if counted_verses != int(manifest["verse_count"]): fail("verse total mismatch")
    if counted_gaps != int(manifest.get("empty_source_locus_count") or 0): fail("source-gap total mismatch")

    gen = load(books_root / "GEN.json")
    gen1 = (gen.get("chapters") or {}).get("1") or {}
    if len(gen1) != 31 or not (gen1.get("1") or {}).get("surface"): fail("Genesis 1 acceptance locus failed")
    deu = load(books_root / "DEU.json")
    deu_gaps = {(str(g.get("source_chapter")), str(g.get("source_verse"))) for g in (deu.get("empty_source_loci_not_auto_served") or [])}
    if ("25", "19") not in deu_gaps: fail("known pinned Deuteronomy 25:19 empty TEI locus was not preserved as a gap")
    if "19" in (((deu.get("chapters") or {}).get("25")) or {}): fail("Deuteronomy 25:19 must not be fabricated")
    ezr = load(books_root / "EZR.json")
    neh = load(books_root / "NEH.json")
    if set((ezr.get("chapters") or {}).keys()) != {str(i) for i in range(1,11)}: fail("Ezra chapter split changed")
    if set((neh.get("chapters") or {}).keys()) != {str(i) for i in range(1,14)}: fail("Nehemiah chapter split changed")

    print(
        f"Validated OT Septuagint protocanonical production: {manifest['book_count']} books, "
        f"{manifest['chapter_count']} chapters, {manifest['verse_count']} nonempty numeric source verse surfaces, "
        f"{manifest.get('empty_source_locus_count', 0)} explicit source gaps"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
