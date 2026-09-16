#!/usr/bin/env python3
"""Validate the Logos Old Testament Phase 1A source lock and generated corpus."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE_ROOT = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "old_testament_phase1"
LOCK_PATH = PHASE_ROOT / "source-lock.json"
LXX_GATE_PATH = PHASE_ROOT / "lxx-inventory-gate.json"
SOURCES_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "sources-manifest.json"
BOOKS_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "books.json"
DEFAULT_GENERATED = ROOT / "build" / "logos-old-testament-phase1"
HEX40_RE = re.compile(r"^[0-9a-f]{40}$")
HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

EXPECTED_OSHB_COMMIT = "3d15126fb1ef74867fc1434be1942e837932691f"
EXPECTED_WLC_TREE = "dd2fe9d2168f3fc0963bcdbdac8fa1d487c06e45"
EXPECTED_LXX_COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
EXPECTED_LXX_TREE = "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79"
EXPECTED_BOOK_IDS = [
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
    "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
    "ECC", "SNG", "ISA", "JER", "LAM", "EZK", "DAN", "HOS", "JOL", "AMO",
    "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL",
]
EXPECTED_EXCLUDED = {
    "Tobit",
    "Judith",
    "Greek additions to Esther",
    "1 Maccabees",
    "2 Maccabees",
    "Wisdom",
    "Sirach",
    "Baruch",
    "Greek additions to Daniel",
}


class ValidationError(RuntimeError):
    pass


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def source_by_id(manifest: dict, source_id: str) -> dict:
    for row in manifest.get("sources") or []:
        if row.get("id") == source_id:
            return row
    raise ValidationError(f"missing source registry entry: {source_id}")


def validate_static() -> None:
    lock = load(LOCK_PATH)
    gate = load(LXX_GATE_PATH)
    sources = load(SOURCES_PATH)
    books_catalog = load(BOOKS_PATH)

    require(lock.get("phase") == "Old Testament Expansion Phase 1A", "unexpected OT phase name")
    require(lock.get("production_enabled") is False, "OT Phase 1A must not be production-enabled")
    require(lock.get("catholic_ot_complete") is False, "OT Phase 1A must not claim complete Catholic OT coverage")
    source = lock.get("source") or {}
    require(source.get("id") == "oshb", "OT Phase 1A must use the OSHB source registry ID")
    require(source.get("repository") == "openscriptures/morphhb", "unexpected OSHB repository")
    require(source.get("commit") == EXPECTED_OSHB_COMMIT, "unexpected OSHB commit pin")
    require(source.get("tree_sha") == EXPECTED_WLC_TREE, "unexpected OSHB wlc tree pin")
    require(source.get("license") == "CC BY 4.0", "OSHB annotation license must remain CC BY 4.0")
    require(source.get("base_text_rights") == "Public Domain", "WLC base text rights must remain Public Domain")
    require("Do not NFC-normalize" in str(source.get("normalization_policy") or ""), "OSHB no-NFC policy is missing")

    locked_books = lock.get("books") or []
    require(len(locked_books) == 39, f"expected 39 Masoretic source books, got {len(locked_books)}")
    ids = [str(row.get("book_id")) for row in locked_books]
    require(ids == EXPECTED_BOOK_IDS, "OT Phase 1A book order/IDs changed unexpectedly")
    filenames = [str(row.get("filename")) for row in locked_books]
    require(len(set(filenames)) == 39 and all(x.endswith(".xml") for x in filenames), "OT source filenames must be 39 unique XML files")
    require(lock.get("required_non_book_files") == ["VerseMap.xml"], "VerseMap.xml must be the sole locked non-book XML")
    require(set(lock.get("excluded_catholic_ot_material") or []) == EXPECTED_EXCLUDED, "Catholic Greek/deuterocanonical exclusion inventory changed")
    require((lock.get("gloss_policy") or {}).get("installed") is False, "OT Phase 1A must not install glosses")
    require((lock.get("transliteration_policy") or {}).get("installed") is False, "OT Phase 1A must not install transliteration")
    require((lock.get("versification_policy") or {}).get("dra_alignment_enabled") is False, "OT Phase 1A must not silently remap MT to DRA versification")

    source_registry = source_by_id(sources, "oshb")
    require(source_registry.get("production_import_allowed") is True, "OSHB source registry must allow controlled ingestion")
    require(source_registry.get("license_verified") is True, "OSHB license must be verified")
    require(source_registry.get("source_inventory_verified") is True, "OSHB source inventory gate must be verified")
    require((source_registry.get("pin") or {}).get("value") == EXPECTED_OSHB_COMMIT, "source registry OSHB pin differs from Phase 1A pin")
    require(source_registry.get("license") == "CC BY 4.0", "source registry OSHB license mismatch")

    lxx_registry = source_by_id(sources, "first1kgreek-swete")
    require(lxx_registry.get("production_import_allowed") is False, "First1KGreek/Swete must remain blocked from production import")
    require(lxx_registry.get("source_inventory_verified") is False, "First1KGreek/Swete inventory must remain pending")
    require(lxx_registry.get("share_alike") is True and lxx_registry.get("isolation_required") is True, "LXX ShareAlike isolation boundary changed")
    require((lxx_registry.get("pin") or {}).get("value") == EXPECTED_LXX_COMMIT, "LXX registry commit pin mismatch")

    require(gate.get("production_enabled") is False, "LXX inventory gate must not be production-enabled")
    require(gate.get("production_import_allowed") is False, "LXX inventory gate must remain blocked")
    require(gate.get("status") == "blocked-pending-exact-catholic-book-mapping", "unexpected LXX inventory gate status")
    gate_source = gate.get("source") or {}
    require(gate_source.get("repository") == "OpenGreekAndLatin/First1KGreek", "unexpected LXX candidate repository")
    require(gate_source.get("commit") == EXPECTED_LXX_COMMIT, "unexpected LXX candidate commit")
    require(gate_source.get("septuagint_tree_sha") == EXPECTED_LXX_TREE, "unexpected Septuagint tlg0527 tree pin")
    require(gate_source.get("license") == "CC BY-SA 4.0", "LXX gate must preserve CC BY-SA 4.0")
    require(gate_source.get("share_alike") is True and gate_source.get("isolation_required") is True, "LXX gate must require ShareAlike isolation")
    require(set(gate.get("required_catholic_mapping_scope") or []) == EXPECTED_EXCLUDED, "LXX Catholic mapping scope is incomplete")
    require((gate.get("known_repository_evidence") or {}).get("exact_catholic_book_inventory_complete") is False, "LXX gate may not claim completed Catholic inventory")

    catalog_books = {str(row.get("id")): row for row in (books_catalog.get("books") or [])}
    require(len(catalog_books) == 73, "canonical books registry must still contain 73 books")
    for row in locked_books:
        book_id = str(row["book_id"])
        catalog = catalog_books.get(book_id)
        require(catalog is not None, f"locked OT source book is absent from Catholic books registry: {book_id}")
        require(catalog.get("testament") == "OT", f"locked source book is not OT in books registry: {book_id}")
        require(str(catalog.get("name")) == str(row.get("name")), f"book-name mismatch for {book_id}")
    require(catalog_books["EST"].get("profile") == "esther-composite", "Esther must remain a composite Catholic OT profile")
    require(catalog_books["DAN"].get("profile") == "daniel-composite", "Daniel must remain a composite Catholic OT profile")


def iter_tokens(payload: dict):
    for chapter in (payload.get("chapters") or {}).values():
        for verse in chapter.values():
            for token in verse.get("tokens") or []:
                yield token


def validate_generated(generated: Path) -> None:
    manifest = load(generated / "manifest.json")
    require(manifest.get("production_enabled") is False, "generated OT corpus must remain production-disabled")
    require(manifest.get("catholic_ot_complete") is False, "generated OT corpus must not claim full Catholic OT")
    require(manifest.get("masoretic_book_witness_count") == 39, "generated OT corpus must contain 39 source books")
    require(int(manifest.get("chapter_count") or 0) > 900, "generated OT chapter count is unexpectedly low")
    require(int(manifest.get("verse_count") or 0) > 23000, "generated OT verse count is unexpectedly low")
    require(int(manifest.get("token_count") or 0) > 400000, "generated OT token count is unexpectedly low")
    require(int(manifest.get("hebrew_token_count") or 0) > 390000, "generated Hebrew token count is unexpectedly low")
    require(int(manifest.get("aramaic_token_count") or 0) > 1000, "generated Aramaic token count is unexpectedly low")
    require(int(manifest.get("alignment_mismatch_count") or -1) == 0, "generated OT alignment contains mismatches")
    require(manifest.get("surface_normalization_applied") is False, "generated OT corpus must preserve source Unicode without normalization")
    require((manifest.get("gloss_layer") or {}).get("installed") is False, "generated OT corpus unexpectedly installed glosses")
    require((manifest.get("transliteration_layer") or {}).get("installed") is False, "generated OT corpus unexpectedly installed transliteration")
    require((manifest.get("dra_versification_alignment") or {}).get("enabled") is False, "generated OT corpus unexpectedly remapped DRA versification")

    source = manifest.get("source") or {}
    require(source.get("commit") == EXPECTED_OSHB_COMMIT, "generated OT source commit mismatch")
    require(source.get("tree_sha") == EXPECTED_WLC_TREE, "generated OT source tree mismatch")
    require(source.get("base_text_rights") == "Public Domain", "generated OT WLC rights mismatch")
    require(source.get("annotation_license") == "CC BY 4.0", "generated OT annotation license mismatch")
    require(HEX40_RE.fullmatch(str(source.get("verse_map_git_blob_sha1") or "")) is not None, "VerseMap Git blob SHA missing")
    require(HEX64_RE.fullmatch(str(source.get("verse_map_sha256") or "")) is not None, "VerseMap SHA-256 missing")

    book_stats = manifest.get("books") or []
    require([row.get("book_id") for row in book_stats] == EXPECTED_BOOK_IDS, "generated OT book order differs from source lock")
    for row in book_stats:
        require(HEX40_RE.fullmatch(str(row.get("source_git_blob_sha1") or "")) is not None, f"missing Git blob SHA for {row.get('book_id')}")
        require(HEX64_RE.fullmatch(str(row.get("source_sha256") or "")) is not None, f"missing SHA-256 for {row.get('book_id')}")
        require(int(row.get("verse_count") or 0) > 0 and int(row.get("token_count") or 0) > 0, f"empty generated book {row.get('book_id')}")

    for partition in ("surface", "linguistics", "alignment"):
        paths = sorted((generated / partition).glob("*.json"))
        require(len(paths) == 39, f"expected 39 generated {partition} files, got {len(paths)}")
        require({p.stem for p in paths} == set(EXPECTED_BOOK_IDS), f"generated {partition} book set mismatch")

    total_surface_tokens = 0
    total_linguistic_tokens = 0
    languages: set[str] = set()
    for book_id in EXPECTED_BOOK_IDS:
        surface = load(generated / "surface" / f"{book_id}.json")
        linguistics = load(generated / "linguistics" / f"{book_id}.json")
        alignment = load(generated / "alignment" / f"{book_id}.json")
        require(surface.get("normalization_applied") is False, f"source normalization marker changed in {book_id}")
        require(alignment.get("mismatch_count") == 0, f"alignment mismatch in {book_id}")

        surface_tokens = list(iter_tokens(surface))
        linguistic_tokens = list(iter_tokens(linguistics))
        require(len(surface_tokens) == len(linguistic_tokens), f"surface/linguistic token count mismatch in {book_id}")
        total_surface_tokens += len(surface_tokens)
        total_linguistic_tokens += len(linguistic_tokens)
        for s_token, l_token in zip(surface_tokens, linguistic_tokens):
            require(s_token.get("id") == l_token.get("id"), f"partition token ID mismatch in {book_id}")
            require(s_token.get("language") == l_token.get("language"), f"partition language mismatch in {book_id}")
            require(s_token.get("surface") not in (None, ""), f"empty source surface in {book_id}")
            require("transliteration" not in s_token and "gloss" not in s_token, f"unapproved derived field in surface token for {book_id}")
            require("transliteration" not in l_token and "gloss" not in l_token, f"unapproved derived field in linguistic token for {book_id}")
            require(l_token.get("lemma") not in (None, ""), f"missing lemma in {book_id}")
            require(l_token.get("morphology") not in (None, ""), f"missing morphology in {book_id}")
            require(l_token.get("source_word_id") not in (None, ""), f"missing immutable OSHB word ID in {book_id}")
            languages.add(str(l_token.get("language")))

    require(total_surface_tokens == int(manifest["token_count"]), "manifest/surface token total mismatch")
    require(total_linguistic_tokens == int(manifest["token_count"]), "manifest/linguistic token total mismatch")
    require(languages == {"he", "arc"}, f"expected Hebrew and Aramaic token languages, got {languages}")

    genesis = load(generated / "surface" / "GEN.json")
    genesis_ling = load(generated / "linguistics" / "GEN.json")
    gen11 = genesis["chapters"]["1"]["1"]["tokens"]
    gen11_ling = genesis_ling["chapters"]["1"]["1"]["tokens"]
    require(gen11[0]["surface"] == "בְּ/רֵאשִׁ֖ית", "Genesis 1:1 first source token changed")
    require(gen11_ling[0]["lemma"] == "b/7225", "Genesis 1:1 first lemma changed")
    require(gen11_ling[0]["morphology"] == "HR/Ncfsa", "Genesis 1:1 first morphology changed")
    require(gen11_ling[0]["source_word_id"] == "01xeN", "Genesis 1:1 immutable source word ID changed")

    daniel = load(generated / "linguistics" / "DAN.json")
    dan24 = daniel["chapters"]["2"]["4"]["tokens"]
    dan24_languages = {row["language"] for row in dan24}
    require(dan24_languages == {"he", "arc"}, "Daniel 2:4 must preserve its Hebrew-to-Aramaic transition")
    require(any(str(row.get("morphology", "")).startswith("A") for row in dan24), "Daniel 2:4 lacks Aramaic morphology evidence")

    require(
        (manifest.get("catholic_scope") or {}).get("esther_and_daniel_status")
        == "Masoretic portions only; Catholic Greek additions pending separate source gate",
        "Catholic Esther/Daniel completeness boundary missing",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated", type=Path, default=None)
    args = parser.parse_args()
    validate_static()
    if args.generated is not None:
        validate_generated(args.generated.resolve())
        print("Logos OT Phase 1A static + generated corpus validation: OK")
    else:
        print("Logos OT Phase 1A static source-lock validation: OK")


if __name__ == "__main__":
    try:
        main()
    except ValidationError as exc:
        raise SystemExit(str(exc))
