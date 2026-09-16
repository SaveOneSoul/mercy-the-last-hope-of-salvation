#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_ot_catholic_full"
ISOLATED = Path("sharealike/catholic_lxx_cc-by-sa-4.0")
FIRST1K_COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
FIRST1K_TREE = "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79"
ECC_COMMIT = "338aa27310b3cfe2588a993b4d113b503597d70f"
ECC_BLOB = "1659770789d318e7ee04f3ee03684bf880922bc4"
EXPECTED_BOOKS = {
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA", "1KI", "2KI",
    "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO", "ECC", "SNG", "ISA", "JER",
    "LAM", "EZK", "DAN", "HOS", "JOL", "AMO", "OBA", "JON", "MIC", "NAM", "HAB", "ZEP",
    "HAG", "ZEC", "MAL",
}


def fail(message: str) -> None:
    raise SystemExit(f"Full Catholic Greek OT validation failed: {message}")


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {path}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = load(root / "manifest.json")

    if manifest.get("corpus_id") != "grc_ot_catholic_full" or manifest.get("production_enabled") is not True:
        fail("unexpected corpus identity or production flag")
    if int(manifest.get("book_count") or 0) != 39:
        fail("package must contain exactly 39 protocanonical Catholic book scopes")
    if int(manifest.get("first1k_swete_book_scope_count") or 0) != 38:
        fail("package must preserve exactly 38 First1K/Swete book scopes")
    if int(manifest.get("ecclesiastes_fallback_book_scope_count") or 0) != 1:
        fail("package must contain exactly one explicit Ecclesiastes fallback scope")
    if int(manifest.get("verse_record_count") or 0) < 20000:
        fail("Greek OT verse inventory is unexpectedly incomplete")

    sources = manifest.get("sources") or {}
    first1k = sources.get("first1k_swete") or {}
    if first1k.get("repository") != "OpenGreekAndLatin/First1KGreek" or first1k.get("commit") != FIRST1K_COMMIT:
        fail("immutable First1K source pin changed")
    if first1k.get("septuagint_tree_sha") != FIRST1K_TREE:
        fail("immutable First1K Septuagint tree pin changed")
    if first1k.get("license") != "CC BY-SA 4.0" or first1k.get("share_alike") is not True or first1k.get("isolation_required") is not True:
        fail("First1K rights/isolation contract changed")

    ecclesiastes = sources.get("ecclesiastes") or {}
    if ecclesiastes.get("repository") != "open-greek/open-greek-corpus" or ecclesiastes.get("commit") != ECC_COMMIT:
        fail("Ecclesiastes fallback immutable source pin changed")
    if ecclesiastes.get("git_blob_sha1") != ECC_BLOB:
        fail("Ecclesiastes fallback Git blob identity changed")
    if ecclesiastes.get("license") != "CC BY-SA 4.0" or ecclesiastes.get("share_alike") is not True or ecclesiastes.get("isolation_required") is not True:
        fail("Ecclesiastes fallback rights/isolation contract changed")
    if ecclesiastes.get("first1k_gap_verified") is not True:
        fail("Ecclesiastes First1K gap evidence is missing")
    if int(ecclesiastes.get("chapter_count") or 0) != 12 or int(ecclesiastes.get("verse_count") or 0) != 222:
        fail("Ecclesiastes fallback inventory changed")

    partition = manifest.get("partition") or {}
    if partition.get("path") != str(ISOLATED) or partition.get("share_alike") is not True or partition.get("isolation_required") is not True:
        fail("ShareAlike partition contract changed")
    runtime = manifest.get("runtime_contract") or {}
    if runtime.get("local_only") is not True or runtime.get("automatic_versification_remapping") is not False:
        fail("runtime safety contract changed")
    if runtime.get("source_boundaries_preserved") is not True or runtime.get("empty_source_divisions_preserved") is not True:
        fail("source-boundary preservation contract changed")
    if runtime.get("deuterocanonical_package") != "grc_ot_catholic_swete":
        fail("accepted deuterocanonical companion package contract changed")
    if runtime.get("ecclesiastes_not_swete") is not True:
        fail("Ecclesiastes must remain explicitly distinguished from Swete")
    derived = manifest.get("derived_layers") or {}
    if any(derived.get(key) is not False for key in ("glosses", "lemmata", "morphology", "transliteration")):
        fail("unavailable LXX linguistic layers must remain disabled")

    stats = manifest.get("books") or []
    ids = {str(row.get("book_id") or "") for row in stats}
    if ids != EXPECTED_BOOKS or len(stats) != 39:
        fail(f"39-book scope mismatch: {sorted(ids ^ EXPECTED_BOOKS)}")
    source_families = {str(row.get("book_id")): str(row.get("source_family") or "") for row in stats}
    if source_families.get("ECC") != "open-greek-wikisource-ecclesiastes":
        fail("Ecclesiastes source family is not the explicit pinned fallback")
    if any(family != "first1k-swete" for book_id, family in source_families.items() if book_id != "ECC"):
        fail("non-Ecclesiastes protocanonical book unexpectedly left the First1K/Swete source family")

    book_dir = root / ISOLATED / "books"
    files = list(book_dir.glob("*.json"))
    if len(files) != 39:
        fail(f"expected 39 isolated Greek book files, found {len(files)}")

    total = 0
    empty_loci: set[tuple[str, str]] = set()
    for book_id in sorted(EXPECTED_BOOKS):
        payload = load(book_dir / f"{book_id}.json")
        if payload.get("book_id") != book_id or payload.get("corpus_id") != "grc_ot_catholic_full":
            fail(f"{book_id}: book identity changed")
        if payload.get("license") != "CC BY-SA 4.0" or payload.get("share_alike") is not True or payload.get("isolation_required") is not True:
            fail(f"{book_id}: rights/isolation metadata changed")
        source_row = payload.get("source") or {}
        if source_row.get("per_file_license_verified") is not True:
            fail(f"{book_id}: source licence evidence is incomplete")
        if book_id == "ECC":
            if source_row.get("source_family") != "open-greek-wikisource-ecclesiastes":
                fail("ECC: source family changed")
            if source_row.get("repository") != "open-greek/open-greek-corpus" or source_row.get("commit") != ECC_COMMIT:
                fail("ECC: fallback source pin changed")
            if source_row.get("git_blob_sha1") != ECC_BLOB or not source_row.get("sha256"):
                fail("ECC: fallback source integrity evidence incomplete")
            if source_row.get("first1k_gap_verified") is not True:
                fail("ECC: First1K gap evidence missing")
        else:
            if source_row.get("source_family") != "first1k-swete":
                fail(f"{book_id}: expected First1K/Swete source family")
            if source_row.get("repository") != "OpenGreekAndLatin/First1KGreek" or source_row.get("commit") != FIRST1K_COMMIT:
                fail(f"{book_id}: First1K source pin changed")
            if not source_row.get("text_sha256") or not source_row.get("text_git_blob_sha1"):
                fail(f"{book_id}: First1K integrity evidence incomplete")
        surface_policy = payload.get("surface_policy") or {}
        if surface_policy.get("source_boundaries_preserved") is not True or surface_policy.get("empty_source_divisions_preserved") is not True:
            fail(f"{book_id}: source-surface preservation policy changed")
        verses = payload.get("verses") or []
        if not verses:
            fail(f"{book_id}: no Greek source verses")
        for verse in verses:
            source_reference = str(verse.get("source_reference") or "").strip()
            if not source_reference:
                fail(f"{book_id}: empty source reference")
            surface = str(verse.get("surface") or "")
            if surface:
                if verse.get("source_empty_surface") is True:
                    fail(f"{book_id} {source_reference}: non-empty surface incorrectly marked empty")
            else:
                if verse.get("source_empty_surface") is not True:
                    fail(f"{book_id} {source_reference}: empty source division is not explicitly preserved")
                empty_loci.add((book_id, source_reference))
        total += len(verses)

    if total != int(manifest.get("verse_record_count") or 0):
        fail("manifest verse total does not equal isolated source records")
    if not empty_loci:
        fail("known pinned First1K empty source verse divisions were not preserved")
    if int(manifest.get("empty_source_surface_count") or 0) != len(empty_loci):
        fail("manifest empty-source count does not equal preserved empty divisions")
    manifest_empty = {
        (str(row.get("book_id") or ""), str(row.get("source_reference") or ""))
        for row in (manifest.get("empty_source_surfaces") or [])
    }
    if manifest_empty != empty_loci:
        fail("manifest empty-source locus inventory changed")

    genesis = load(book_dir / "GEN.json")
    gen11 = [row for row in genesis.get("verses") or [] if row.get("source_chapter") == "1" and row.get("source_verse") == "1"]
    if len(gen11) != 1 or not str(gen11[0].get("surface") or "").strip():
        fail("Genesis 1:1 source sentinel missing")
    eccles = load(book_dir / "ECC.json")
    ecc11 = [row for row in eccles.get("verses") or [] if row.get("source_chapter") == "1" and row.get("source_verse") == "1"]
    if len(ecc11) != 1 or not str(ecc11[0].get("surface") or "").startswith("Ρήματα ἐκκλησιαστοῦ"):
        fail("Ecclesiastes 1:1 fallback sentinel changed")
    if len(eccles.get("verses") or []) != 222:
        fail("Ecclesiastes fallback verse count changed")

    ezra = load(book_dir / "EZR.json")
    nehemiah = load(book_dir / "NEH.json")
    if (ezra.get("mapping") or {}).get("canonical_chapter_offset") != 0:
        fail("Ezra Esdras-B mapping changed")
    if (nehemiah.get("mapping") or {}).get("canonical_chapter_offset") != 10:
        fail("Nehemiah Esdras-B mapping changed")

    print(
        f"Full Catholic Greek OT validation passed: 39 book scopes / {total} source verse records / "
        f"{len(empty_loci)} preserved empty First1K divisions / Ecclesiastes 222-verse pinned fallback"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
