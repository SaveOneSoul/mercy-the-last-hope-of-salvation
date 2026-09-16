#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_ot_swete_full"
ISOLATED = Path("sharealike/first1kgreek_swete_cc-by-sa-4.0")
EXPECTED_COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
EXPECTED_TREE = "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79"
EXPECTED_BOOKS = {
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA", "1KI", "2KI",
    "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO", "ECC", "SNG", "ISA", "JER",
    "LAM", "EZK", "DAN", "HOS", "JOL", "AMO", "OBA", "JON", "MIC", "NAM", "HAB", "ZEP",
    "HAG", "ZEC", "MAL",
}


def fail(message: str) -> None:
    raise SystemExit(f"Full Swete OT validation failed: {message}")


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
    if manifest.get("corpus_id") != "grc_ot_swete_full" or manifest.get("production_enabled") is not True:
        fail("unexpected corpus identity or production flag")
    if int(manifest.get("book_count") or 0) != 39:
        fail("package must contain exactly 39 protocanonical Catholic book scopes")
    if int(manifest.get("verse_record_count") or 0) < 20000:
        fail("Greek OT verse inventory is unexpectedly incomplete")
    source = manifest.get("source") or {}
    if source.get("repository") != "OpenGreekAndLatin/First1KGreek" or source.get("commit") != EXPECTED_COMMIT:
        fail("immutable First1KGreek source pin changed")
    if source.get("septuagint_tree_sha") != EXPECTED_TREE:
        fail("immutable Septuagint tree pin changed")
    if source.get("license") != "CC BY-SA 4.0" or source.get("share_alike") is not True or source.get("isolation_required") is not True:
        fail("Greek OT rights/isolation contract changed")
    partition = manifest.get("partition") or {}
    if partition.get("path") != str(ISOLATED) or partition.get("share_alike") is not True or partition.get("isolation_required") is not True:
        fail("ShareAlike partition contract changed")
    runtime = manifest.get("runtime_contract") or {}
    if runtime.get("local_only") is not True or runtime.get("automatic_versification_remapping") is not False:
        fail("runtime safety contract changed")
    if runtime.get("deuterocanonical_package") != "grc_ot_catholic_swete":
        fail("accepted deuterocanonical companion package contract changed")
    derived = manifest.get("derived_layers") or {}
    if any(derived.get(key) is not False for key in ("glosses", "lemmata", "morphology", "transliteration")):
        fail("unavailable LXX linguistic layers must remain disabled")

    stats = manifest.get("books") or []
    ids = {str(row.get("book_id") or "") for row in stats}
    if ids != EXPECTED_BOOKS or len(stats) != 39:
        fail(f"39-book scope mismatch: {sorted(ids ^ EXPECTED_BOOKS)}")
    book_dir = root / ISOLATED / "books"
    files = list(book_dir.glob("*.json"))
    if len(files) != 39:
        fail(f"expected 39 isolated Greek book files, found {len(files)}")
    total = 0
    for book_id in sorted(EXPECTED_BOOKS):
        payload = load(book_dir / f"{book_id}.json")
        if payload.get("book_id") != book_id or payload.get("corpus_id") != "grc_ot_swete_full":
            fail(f"{book_id}: book identity changed")
        if payload.get("license") != "CC BY-SA 4.0" or payload.get("share_alike") is not True or payload.get("isolation_required") is not True:
            fail(f"{book_id}: rights/isolation metadata changed")
        source_row = payload.get("source") or {}
        if source_row.get("repository") != "OpenGreekAndLatin/First1KGreek" or source_row.get("commit") != EXPECTED_COMMIT:
            fail(f"{book_id}: source pin changed")
        if source_row.get("per_file_license_verified") is not True or not source_row.get("text_sha256") or not source_row.get("text_git_blob_sha1"):
            fail(f"{book_id}: source integrity/licence evidence incomplete")
        verses = payload.get("verses") or []
        if not verses:
            fail(f"{book_id}: no Greek source verses")
        for verse in verses:
            if not str(verse.get("surface") or "").strip() or not str(verse.get("source_reference") or "").strip():
                fail(f"{book_id}: empty source surface/reference")
        total += len(verses)
    if total != int(manifest.get("verse_record_count") or 0):
        fail("manifest verse total does not equal isolated source records")

    genesis = load(book_dir / "GEN.json")
    gen11 = [row for row in genesis.get("verses") or [] if row.get("source_chapter") == "1" and row.get("source_verse") == "1"]
    if len(gen11) != 1 or not str(gen11[0].get("surface") or "").strip():
        fail("Genesis 1:1 source sentinel missing")
    ezra = load(book_dir / "EZR.json")
    nehemiah = load(book_dir / "NEH.json")
    if (ezra.get("mapping") or {}).get("canonical_chapter_offset") != 0:
        fail("Ezra Esdras-B mapping changed")
    if (nehemiah.get("mapping") or {}).get("canonical_chapter_offset") != 10:
        fail("Nehemiah Esdras-B mapping changed")

    print(f"Full Swete OT validation passed: 39 book scopes / {total} source verse records")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
