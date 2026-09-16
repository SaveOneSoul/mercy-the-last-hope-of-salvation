#!/usr/bin/env python3
"""Validate Logos Old Testament Phase 1B source locks, mappings, and generated evidence."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE_ROOT = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "old_testament_phase1b"
LOCK_PATH = PHASE_ROOT / "source-lock.json"
MAP_PATH = PHASE_ROOT / "versification-map.json"
GATE_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "old_testament_phase1" / "lxx-inventory-gate.json"
SOURCES_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "sources-manifest.json"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")

SOURCE_COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
SOURCE_TREE = "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79"
PHASE1B_ACCEPTANCE_MERGE = "22ad0019355d6924592d3c6b5176624e6fd4c866"
ISOLATED_ROOT = "sharealike/first1kgreek_swete_cc-by-sa-4.0"
EXPECTED_TOTAL_VERSES = 5337
EXPECTED_IDS = [
    "EST-SWETE", "JDT-SWETE", "TOB-SWETE", "1MA-SWETE", "2MA-SWETE",
    "WIS-SWETE", "SIR-SWETE", "BAR-SWETE", "EPJ-SWETE",
    "SUS-OG-SWETE", "SUS-TH-SWETE", "DAN-OG-SWETE", "DAN-TH-SWETE",
    "BEL-OG-SWETE", "BEL-TH-SWETE",
]
PARALLEL_IDS = {"SUS-OG-SWETE", "DAN-OG-SWETE", "BEL-OG-SWETE"}
THEODOTION_IDS = {"SUS-TH-SWETE", "DAN-TH-SWETE", "BEL-TH-SWETE"}


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


def by_id(rows: list[dict]) -> dict[str, dict]:
    return {str(row.get("id")): row for row in rows}


def validate_static() -> None:
    lock = load(LOCK_PATH)
    mapping = load(MAP_PATH)
    gate = load(GATE_PATH)
    sources = load(SOURCES_PATH)

    need(lock.get("phase") == "Old Testament Expansion Phase 1B", "unexpected Phase 1B lock identity")
    need(lock.get("production_enabled") is False and lock.get("production_import_allowed") is False, "Phase 1B evidence must remain production-disabled")
    need(lock.get("owner_acceptance_required") is True, "Phase 1B owner-acceptance gate missing")
    source = lock.get("source") or {}
    need(source.get("repository") == "OpenGreekAndLatin/First1KGreek", "unexpected Phase 1B repository")
    need(source.get("commit") == SOURCE_COMMIT and source.get("septuagint_tree_sha") == SOURCE_TREE, "Phase 1B immutable source pin mismatch")
    need(source.get("license") == "CC BY-SA 4.0", "Phase 1B licence mismatch")
    need(source.get("share_alike") is True and source.get("isolation_required") is True, "Phase 1B ShareAlike isolation missing")
    need(source.get("output_partition") == ISOLATED_ROOT, "Phase 1B isolation root changed")

    fidelity = lock.get("fidelity_policy") or {}
    for key in ("glosses", "lemmata", "morphology", "transliteration", "english_text_copied"):
        need(fidelity.get(key) is False, f"unapproved Phase 1B derived/content layer enabled: {key}")
    need(fidelity.get("unicode_normalization") == "none", "Phase 1B source Unicode normalization must stay disabled")

    witnesses = lock.get("witnesses") or []
    need(len(witnesses) == 15, "Phase 1B must pin exactly 15 witnesses")
    need([str(row.get("id")) for row in witnesses] == EXPECTED_IDS, "Phase 1B witness inventory/order changed")
    ids = by_id(witnesses)
    for row in witnesses:
        wid = str(row["id"])
        for field in ("metadata_git_blob_sha1", "text_git_blob_sha1"):
            need(HEX40.fullmatch(str(row.get(field) or "")) is not None, f"{wid}: invalid {field}")
        need(str(row.get("metadata_path") or "").startswith("data/tlg0527/"), f"{wid}: metadata escaped locked tree")
        need(str(row.get("text_path") or "").startswith("data/tlg0527/"), f"{wid}: text escaped locked tree")
        need(str(row.get("edition_urn") or "").startswith("urn:cts:greekLit:tlg0527."), f"{wid}: invalid CTS edition URN")

    need(ids["SIR-SWETE"].get("edition_urn") == "urn:cts:greekLit:tlg0527.tlg034.1st1K-grc2", "Sirach must select the Swete grc2 edition")
    need(ids["SIR-SWETE"].get("rejected_alternate_edition") == "urn:cts:greekLit:tlg0527.tlg034.1st1K-grc1", "Sirach alternate-edition rejection missing")
    need({wid for wid, row in ids.items() if row.get("witness_role") == "preserved-parallel-witness"} == PARALLEL_IDS, "Old Greek parallel witness inventory changed")
    need(THEODOTION_IDS.issubset({wid for wid, row in ids.items() if row.get("witness_role") == "primary-catholic-integration"}), "Theodotion integration witnesses missing")

    need(mapping.get("production_enabled") is False, "accepted versification evidence itself must remain validation-only")
    identity = {str(x.get("witness_id")): x for x in mapping.get("identity_books") or []}
    need(set(identity) == {"TOB-SWETE", "JDT-SWETE", "1MA-SWETE", "2MA-SWETE", "WIS-SWETE", "SIR-SWETE"}, "identity-book map changed")
    need(all(x.get("mapping") == "identity-chapter-verse" for x in identity.values()), "identity mapping must stay explicit")

    baruch = mapping.get("baruch") or {}
    baruch_segments = {str(x.get("witness_id")): x for x in baruch.get("segments") or []}
    need(baruch_segments.get("BAR-SWETE", {}).get("canonical_locus") == "BAR 1-5", "Baruch 1-5 map missing")
    need(baruch_segments.get("EPJ-SWETE", {}).get("canonical_locus") == "BAR 6:1-n", "Epistle of Jeremiah -> Baruch 6 map missing")

    esther = mapping.get("esther") or {}
    need(esther.get("mapping_granularity") == "component-range", "Esther must use component-range mapping")
    esther_components = {str(x.get("component")): x for x in esther.get("components") or []}
    expected_esther = {
        "A": "EST 11:2-12:6", "B1-7": "EST 13:1-7", "C": "EST 13:8-14:19",
        "B8-9": "EST 15:1-3", "D": "EST 15:4-19", "E": "EST 16:1-24",
        "F1-10": "EST 10:4-13", "F11-postscript": "EST 11:1",
    }
    need({key: row.get("canonical_locus") for key, row in esther_components.items()} == expected_esther, "Esther Catholic component mapping changed")
    need(esther_components["B8-9"].get("mapping") == "component-range-no-forced-verse-split", "Esther B8-9 must not be forced into one-to-one verses")

    daniel = mapping.get("daniel") or {}
    need(daniel.get("primary_integration_witness") == "Theodotion" and daniel.get("parallel_witness") == "Old Greek", "Daniel witness policy changed")
    primary = {str(x.get("witness_id")): x for x in daniel.get("primary_segments") or []}
    need(primary.get("DAN-TH-SWETE", {}).get("canonical_locus") == "DAN 3:24-90", "Daniel 3 Greek addition map missing")
    need(primary.get("SUS-TH-SWETE", {}).get("source_locus") == "Susanna 1-64", "Susanna source range changed")
    need(primary.get("SUS-TH-SWETE", {}).get("canonical_locus") == "DAN 13:1-64", "Susanna map missing")
    need(primary.get("BEL-TH-SWETE", {}).get("source_locus") == "Bel and the Dragon 1:1-36", "Bel source range changed")
    need(primary.get("BEL-TH-SWETE", {}).get("canonical_locus") == "DAN 14:1-42", "Bel Catholic range map missing")
    need(primary.get("BEL-TH-SWETE", {}).get("mapping") == "component-range-no-forced-verse-split", "Bel must preserve its source/Douay verse-boundary difference")
    parallel = {str(x.get("witness_id")): x for x in daniel.get("parallel_segments") or []}
    need(set(parallel) == PARALLEL_IDS and all(x.get("canonical_replacement") is False for x in parallel.values()), "Old Greek parallel-witness preservation changed")

    need(gate.get("production_enabled") is False and gate.get("production_import_allowed") is False, "Phase 1B evidence gate itself must remain validation-only")
    need(gate.get("status") == "accepted-production-integration-authorized", "Phase 1B acceptance state missing")
    gate_evidence = gate.get("known_repository_evidence") or {}
    need(gate_evidence.get("owner_accepted") is True, "Phase 1B owner acceptance not recorded")
    need(gate_evidence.get("owner_acceptance_merge_commit") == PHASE1B_ACCEPTANCE_MERGE, "Phase 1B owner-acceptance merge mismatch")

    first1k = next((x for x in sources.get("sources") or [] if x.get("id") == "first1kgreek-swete"), None)
    need(first1k is not None, "First1KGreek source registry entry missing")
    need(first1k.get("status") == "approved-for-production-ingestion", "central source registry acceptance state missing")
    need(first1k.get("production_import_allowed") is True and first1k.get("source_inventory_verified") is True, "central source registry must reflect accepted Phase 1B inventory")
    need(first1k.get("share_alike") is True and first1k.get("isolation_required") is True, "central ShareAlike boundary changed")
    need((first1k.get("owner_acceptance") or {}).get("merge_commit") == PHASE1B_ACCEPTANCE_MERGE, "central registry acceptance merge mismatch")


def witness_path(root: Path, witness_id: str) -> Path:
    return root / ISOLATED_ROOT / "witnesses" / f"{witness_id}.json"


def has_ref(payload: dict, chapter: str | None, verse: str) -> bool:
    return any(row.get("source_chapter") == chapter and str(row.get("source_verse")) == verse for row in payload.get("verses") or [])


def has_verse_number(payload: dict, verse: str) -> bool:
    return any(str(row.get("source_verse")) == verse for row in payload.get("verses") or [])


def scan_forbidden(value, path: str = "root") -> None:
    forbidden = {"gloss", "lemma", "lemmata", "morphology", "transliteration", "english_text", "english_scripture"}
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in forbidden:
                raise ValidationError(f"unapproved field {key!r} found at {path}")
            scan_forbidden(item, f"{path}.{key}")
    elif isinstance(value, list):
        for i, item in enumerate(value):
            scan_forbidden(item, f"{path}[{i}]")


def validate_generated(root: Path) -> None:
    entries = sorted(p.name for p in root.iterdir()) if root.exists() else []
    need(entries == ["sharealike"], f"Phase 1B output must contain only isolated ShareAlike data; got {entries}")
    isolated = root / ISOLATED_ROOT
    manifest = load(isolated / "manifest.json")
    need(manifest.get("production_enabled") is False and manifest.get("production_import_allowed") is False, "generated Phase 1B corpus must remain disabled")
    need(manifest.get("witness_count") == 15, "generated witness count must be 15")
    need(manifest.get("verse_record_count") == EXPECTED_TOTAL_VERSES, f"generated source verse total changed: expected {EXPECTED_TOTAL_VERSES}, got {manifest.get('verse_record_count')}")
    source = manifest.get("source") or {}
    need(source.get("commit") == SOURCE_COMMIT and source.get("septuagint_tree_sha") == SOURCE_TREE, "generated immutable source pin mismatch")
    need(source.get("license") == "CC BY-SA 4.0" and source.get("share_alike") is True and source.get("isolation_required") is True, "generated ShareAlike boundary missing")
    isolation = manifest.get("isolation") or {}
    need(isolation.get("root") == ISOLATED_ROOT, "generated isolation root mismatch")
    need(isolation.get("english_corpus_unchanged") is True and isolation.get("oshb_corpus_unchanged") is True and isolation.get("greek_nt_corpus_unchanged") is True, "generated corpus isolation guarantees missing")
    need(isolation.get("contains_english_scripture_text") is False, "Phase 1B must not package English Scripture text")
    need(all(v is False for v in (manifest.get("derived_layers") or {}).values()), "unapproved generated derived layer enabled")

    witness_files = sorted((isolated / "witnesses").glob("*.json"))
    need(len(witness_files) == 15 and [p.stem for p in witness_files] == sorted(EXPECTED_IDS), "generated witness file inventory mismatch")
    lock = load(LOCK_PATH)
    locked = by_id(lock.get("witnesses") or [])
    total = 0
    for wid in EXPECTED_IDS:
        payload = load(witness_path(root, wid))
        need(payload.get("production_enabled") is False, f"{wid}: production unexpectedly enabled")
        need(payload.get("partition") == "sharealike-first1kgreek-swete", f"{wid}: partition marker changed")
        need(payload.get("license") == "CC BY-SA 4.0" and payload.get("share_alike") is True and payload.get("isolation_required") is True, f"{wid}: ShareAlike metadata incomplete")
        src = payload.get("source") or {}
        need(src.get("commit") == SOURCE_COMMIT, f"{wid}: source commit changed")
        need(src.get("metadata_git_blob_sha1") == locked[wid]["metadata_git_blob_sha1"], f"{wid}: metadata blob changed")
        need(src.get("text_git_blob_sha1") == locked[wid]["text_git_blob_sha1"], f"{wid}: text blob changed")
        need(HEX64.fullmatch(str(src.get("metadata_sha256") or "")) is not None, f"{wid}: metadata SHA-256 missing")
        need(HEX64.fullmatch(str(src.get("text_sha256") or "")) is not None, f"{wid}: text SHA-256 missing")
        need(src.get("per_file_license_verified") is True, f"{wid}: per-file licence not verified")
        verses = payload.get("verses") or []
        need(len(verses) > 0, f"{wid}: empty generated witness")
        refs = [(row.get("source_chapter"), str(row.get("source_verse"))) for row in verses]
        need(len(refs) == len(set(refs)), f"{wid}: duplicate source references")
        need(all(str(row.get("surface") or "").strip() for row in verses), f"{wid}: empty source surface")
        scan_forbidden(payload.get("verses") or [], wid)
        total += len(verses)
    need(total == EXPECTED_TOTAL_VERSES == manifest.get("verse_record_count"), "manifest/source verse totals disagree")

    epj = load(witness_path(root, "EPJ-SWETE"))
    need(len(epj.get("verses") or []) == 72 and has_verse_number(epj, "1") and has_verse_number(epj, "72"), "Epistle of Jeremiah expected source range 1-72 not found")
    dan = load(witness_path(root, "DAN-TH-SWETE"))
    need(has_ref(dan, "3", "24") and has_ref(dan, "3", "90"), "Theodotion Daniel 3:24-90 evidence missing")
    sus = load(witness_path(root, "SUS-TH-SWETE"))
    need(len(sus.get("verses") or []) == 64 and has_verse_number(sus, "1") and has_verse_number(sus, "64"), "Theodotion Susanna expected source range 1-64 missing")
    bel = load(witness_path(root, "BEL-TH-SWETE"))
    need(len(bel.get("verses") or []) == 36 and has_ref(bel, "1", "1") and has_ref(bel, "1", "36"), "Theodotion Bel expected pinned Swete source range 1:1-36 missing")
    need(not has_verse_number(bel, "42"), "Theodotion Bel source must not fabricate Douay-Rheims verse 42")
    est = load(witness_path(root, "EST-SWETE"))
    need(has_ref(est, "prologue", "1") and has_ref(est, "prologue", "17"), "Greek Esther prologue Addition A evidence missing")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--generated", type=Path)
    args = parser.parse_args()
    validate_static()
    if args.generated:
        validate_generated(args.generated.resolve())
        manifest = load(args.generated.resolve() / ISOLATED_ROOT / "manifest.json")
        print(
            "Logos OT Phase 1B validation passed: "
            f"15 locked Greek witnesses, {manifest['verse_record_count']} source verse records, "
            "CC BY-SA 4.0 isolated; production evidence remains validation-only"
        )
    else:
        print("Logos OT Phase 1B static source-lock and versification validation: OK")


if __name__ == "__main__":
    try:
        main()
    except ValidationError as exc:
        raise SystemExit(str(exc))
