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
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

OSHB_COMMIT = "3d15126fb1ef74867fc1434be1942e837932691f"
WLC_TREE = "dd2fe9d2168f3fc0963bcdbdac8fa1d487c06e45"
LXX_COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
LXX_TREE = "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79"
PHASE1B_ACCEPTANCE_MERGE = "22ad0019355d6924592d3c6b5176624e6fd4c866"
BOOK_IDS = [
    "GEN", "EXO", "LEV", "NUM", "DEU", "JOS", "JDG", "RUT", "1SA", "2SA",
    "1KI", "2KI", "1CH", "2CH", "EZR", "NEH", "EST", "JOB", "PSA", "PRO",
    "ECC", "SNG", "ISA", "JER", "LAM", "EZK", "DAN", "HOS", "JOL", "AMO",
    "OBA", "JON", "MIC", "NAM", "HAB", "ZEP", "HAG", "ZEC", "MAL",
]
PENDING_GREEK = {
    "Tobit", "Judith", "Greek additions to Esther", "1 Maccabees", "2 Maccabees",
    "Wisdom", "Sirach", "Baruch", "Greek additions to Daniel",
}
EXPECTED_COUNTS = {
    "chapter_count": 929,
    "verse_count": 23213,
    "token_count": 305507,
    "hebrew_token_count": 300679,
    "aramaic_token_count": 4828,
}


class ValidationError(RuntimeError):
    pass


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc


def need(condition: bool, message: str) -> None:
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
    books = load(BOOKS_PATH)

    need(lock.get("phase") == "Old Testament Expansion Phase 1A", "unexpected OT phase")
    need(lock.get("production_enabled") is False, "OT Phase 1A must remain production-disabled")
    need(lock.get("catholic_ot_complete") is False, "Phase 1A must not claim complete Catholic OT coverage")
    src = lock.get("source") or {}
    need(src.get("id") == "oshb" and src.get("repository") == "openscriptures/morphhb", "unexpected OSHB source identity")
    need(src.get("commit") == OSHB_COMMIT and src.get("tree_sha") == WLC_TREE, "OSHB immutable pin mismatch")
    need(src.get("license") == "CC BY 4.0" and src.get("base_text_rights") == "Public Domain", "OSHB/WLC rights mismatch")
    need("Do not NFC-normalize" in str(src.get("normalization_policy") or ""), "OSHB no-NFC rule missing")

    locked = lock.get("books") or []
    need(len(locked) == 39, "Phase 1A must contain exactly 39 Masoretic witnesses")
    need([str(x.get("book_id")) for x in locked] == BOOK_IDS, "Phase 1A Catholic book mapping/order changed")
    filenames = [str(x.get("filename")) for x in locked]
    need(len(set(filenames)) == 39 and all(x.endswith(".xml") for x in filenames), "expected 39 unique OSHB XML files")
    need(lock.get("required_non_book_files") == ["VerseMap.xml"], "VerseMap.xml lock missing")
    need(set(lock.get("excluded_catholic_ot_material") or []) == PENDING_GREEK, "Phase 1A Greek-outside-scope inventory changed")
    need((lock.get("gloss_policy") or {}).get("installed") is False, "gloss layer must remain absent")
    need((lock.get("transliteration_policy") or {}).get("installed") is False, "transliteration must remain absent")
    need((lock.get("versification_policy") or {}).get("dra_alignment_enabled") is False, "MT-to-DRA remapping must remain disabled")

    oshb = source_by_id(sources, "oshb")
    need(oshb.get("production_import_allowed") is True, "OSHB controlled ingestion is not approved")
    need(oshb.get("license_verified") is True and oshb.get("source_inventory_verified") is True, "OSHB registry verification incomplete")
    need((oshb.get("pin") or {}).get("value") == OSHB_COMMIT, "OSHB registry pin mismatch")
    need(oshb.get("license") == "CC BY 4.0", "OSHB registry license mismatch")

    lxx = source_by_id(sources, "first1kgreek-swete")
    need(lxx.get("status") == "approved-for-production-ingestion", "LXX central registry acceptance state missing")
    need(lxx.get("production_import_allowed") is True and lxx.get("source_inventory_verified") is True, "LXX central registry must reflect accepted Phase 1B inventory")
    need(lxx.get("share_alike") is True and lxx.get("isolation_required") is True, "LXX ShareAlike isolation changed")
    need((lxx.get("pin") or {}).get("value") == LXX_COMMIT, "LXX registry commit mismatch")
    need((lxx.get("owner_acceptance") or {}).get("merge_commit") == PHASE1B_ACCEPTANCE_MERGE, "LXX registry owner-acceptance merge mismatch")

    gate_src = gate.get("source") or {}
    need(gate.get("production_enabled") is False and gate.get("production_import_allowed") is False, "Phase 1B evidence gate itself must remain validation-only")
    need(gate.get("status") == "accepted-production-integration-authorized", "LXX gate must record accepted Phase 1B evidence")
    need(gate_src.get("repository") == "OpenGreekAndLatin/First1KGreek", "unexpected LXX candidate repository")
    need(gate_src.get("commit") == LXX_COMMIT and gate_src.get("septuagint_tree_sha") == LXX_TREE, "LXX immutable pin mismatch")
    need(gate_src.get("license") == "CC BY-SA 4.0", "LXX license mismatch")
    need(gate_src.get("share_alike") is True and gate_src.get("isolation_required") is True, "LXX isolation rule missing")
    need(set(gate.get("required_catholic_mapping_scope") or []) == PENDING_GREEK, "LXX Catholic mapping scope incomplete")
    evidence = gate.get("known_repository_evidence") or {}
    need(evidence.get("exact_catholic_book_inventory_complete") is True, "Phase 1B exact Catholic Greek inventory evidence missing")
    need(evidence.get("exact_metadata_and_text_blob_pins_complete") is True, "Phase 1B exact file pin evidence missing")
    need(evidence.get("versification_mapping_complete") is True, "Phase 1B versification evidence missing")
    need(evidence.get("sharealike_isolation_validated") is True, "Phase 1B ShareAlike validation evidence missing")
    need(evidence.get("deterministic_ci_import_validated") is True, "Phase 1B deterministic CI evidence missing")
    need(evidence.get("owner_accepted") is True, "Phase 1B owner acceptance is not recorded")
    need(evidence.get("owner_acceptance_merge_commit") == PHASE1B_ACCEPTANCE_MERGE, "Phase 1B acceptance merge mismatch")

    catalog = {str(row.get("id")): row for row in (books.get("books") or [])}
    need(len(catalog) == 73, "canonical books registry must remain 73 books")
    for row in locked:
        bid = str(row["book_id"])
        need(bid in catalog and catalog[bid].get("testament") == "OT", f"invalid Catholic OT mapping: {bid}")
        need(str(catalog[bid].get("name")) == str(row.get("name")), f"Catholic book name mismatch: {bid}")
    need(catalog["EST"].get("profile") == "esther-composite", "Esther composite profile lost")
    need(catalog["DAN"].get("profile") == "daniel-composite", "Daniel composite profile lost")


def tokens(payload: dict):
    for chapter in (payload.get("chapters") or {}).values():
        for verse in chapter.values():
            yield from verse.get("tokens") or []


def validate_generated(root: Path) -> None:
    manifest = load(root / "manifest.json")
    need(manifest.get("production_enabled") is False, "generated OT corpus must remain production-disabled")
    need(manifest.get("catholic_ot_complete") is False, "generated OT corpus cannot claim full Catholic completeness")
    need(manifest.get("masoretic_book_witness_count") == 39, "generated OT corpus must contain 39 witnesses")
    for key, expected in EXPECTED_COUNTS.items():
        need(manifest.get(key) == expected, f"generated OT {key} changed: expected {expected}, got {manifest.get(key)}")
    need(manifest.get("alignment_mismatch_count") == 0, "generated OT alignment mismatch detected")
    need(manifest.get("surface_normalization_applied") is False, "source Unicode normalization must remain disabled")
    need((manifest.get("gloss_layer") or {}).get("installed") is False, "unexpected OT gloss layer")
    need((manifest.get("transliteration_layer") or {}).get("installed") is False, "unexpected OT transliteration layer")
    need((manifest.get("dra_versification_alignment") or {}).get("enabled") is False, "unexpected MT-to-DRA remapping")

    src = manifest.get("source") or {}
    need(src.get("commit") == OSHB_COMMIT and src.get("tree_sha") == WLC_TREE, "generated OSHB source pin mismatch")
    need(src.get("base_text_rights") == "Public Domain" and src.get("annotation_license") == "CC BY 4.0", "generated rights partitions changed")
    need(HEX40.fullmatch(str(src.get("verse_map_git_blob_sha1") or "")) is not None, "VerseMap Git SHA missing")
    need(HEX64.fullmatch(str(src.get("verse_map_sha256") or "")) is not None, "VerseMap SHA-256 missing")

    stats = manifest.get("books") or []
    need([x.get("book_id") for x in stats] == BOOK_IDS, "generated OT book order changed")
    for row in stats:
        need(HEX40.fullmatch(str(row.get("source_git_blob_sha1") or "")) is not None, f"missing blob SHA: {row.get('book_id')}")
        need(HEX64.fullmatch(str(row.get("source_sha256") or "")) is not None, f"missing SHA-256: {row.get('book_id')}")
        need(int(row.get("verse_count") or 0) > 0 and int(row.get("token_count") or 0) > 0, f"empty generated book: {row.get('book_id')}")

    for partition in ("surface", "linguistics", "alignment"):
        paths = list((root / partition).glob("*.json"))
        need(len(paths) == 39 and {p.stem for p in paths} == set(BOOK_IDS), f"generated {partition} inventory mismatch")

    surface_total = linguistic_total = 0
    found_languages: set[str] = set()
    for bid in BOOK_IDS:
        surface = load(root / "surface" / f"{bid}.json")
        ling = load(root / "linguistics" / f"{bid}.json")
        align = load(root / "alignment" / f"{bid}.json")
        need(surface.get("normalization_applied") is False, f"normalization marker changed: {bid}")
        need(align.get("mismatch_count") == 0, f"alignment mismatch: {bid}")
        st = list(tokens(surface))
        lt = list(tokens(ling))
        need(len(st) == len(lt), f"surface/linguistics token mismatch: {bid}")
        surface_total += len(st)
        linguistic_total += len(lt)
        for s, l in zip(st, lt):
            need(s.get("id") == l.get("id") and s.get("language") == l.get("language"), f"partition token mismatch: {bid}")
            need(s.get("surface") not in (None, ""), f"empty source surface: {bid}")
            need("gloss" not in s and "transliteration" not in s and "gloss" not in l and "transliteration" not in l, f"unapproved derived field: {bid}")
            need(l.get("lemma") not in (None, "") and l.get("morphology") not in (None, "") and l.get("source_word_id") not in (None, ""), f"incomplete linguistic token: {bid}")
            found_languages.add(str(l.get("language")))
    need(surface_total == EXPECTED_COUNTS["token_count"] == linguistic_total, "generated token totals disagree")
    need(found_languages == {"he", "arc"}, f"expected Hebrew+Aramaic, got {found_languages}")

    gen_surface = load(root / "surface" / "GEN.json")["chapters"]["1"]["1"]["tokens"]
    gen_ling = load(root / "linguistics" / "GEN.json")["chapters"]["1"]["1"]["tokens"]
    need(gen_surface[0]["surface"] == "בְּ/רֵאשִׁ֖ית", "Genesis 1:1 source surface changed")
    need(gen_ling[0]["lemma"] == "b/7225", "Genesis 1:1 lemma changed")
    need(gen_ling[0]["morphology"] == "HR/Ncfsa", "Genesis 1:1 morphology changed")
    need(gen_ling[0]["source_word_id"] == "01xeN", "Genesis 1:1 source word ID changed")

    dan24 = load(root / "linguistics" / "DAN.json")["chapters"]["2"]["4"]["tokens"]
    need({x["language"] for x in dan24} == {"he", "arc"}, "Daniel 2:4 Hebrew-to-Aramaic transition lost")
    need(any(str(x.get("morphology") or "").startswith("A") for x in dan24), "Daniel 2:4 Aramaic morphology evidence missing")
    need((manifest.get("catholic_scope") or {}).get("esther_and_daniel_status") == "Masoretic portions only; Catholic Greek additions pending separate source gate", "Phase 1A Catholic Esther/Daniel boundary changed")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated", type=Path)
    args = parser.parse_args()
    validate_static()
    if args.generated:
        validate_generated(args.generated.resolve())
        print(
            "Logos OT Phase 1A validation passed: 39 books, 929 chapters, 23213 verses, "
            "305507 source tokens (300679 Hebrew, 4828 Aramaic), zero alignment mismatches; production disabled"
        )
    else:
        print("Logos OT Phase 1A static source-lock validation: OK")


if __name__ == "__main__":
    try:
        main()
    except ValidationError as exc:
        raise SystemExit(str(exc))
