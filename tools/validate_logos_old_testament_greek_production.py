#!/usr/bin/env python3
"""Validate the production package for accepted Catholic OT Greek witnesses."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_ot_catholic_swete"
SOURCE_LOCK = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "old_testament_phase1b" / "source-lock.json"
VERSIFICATION_MAP = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "old_testament_phase1b" / "versification-map.json"
SOURCES_MANIFEST = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "sources-manifest.json"
CORPUS_ID = "grc_ot_catholic_swete"
CORPUS_VERSION = "2026.09.16-swete-catholic-greek-15"
PHASE1B_ACCEPTANCE_MERGE = "22ad0019355d6924592d3c6b5176624e6fd4c866"
SOURCE_COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
SOURCE_TREE = "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79"
ISOLATED_ROOT = "sharealike/first1kgreek_swete_cc-by-sa-4.0"
EXPECTED_WITNESS_COUNT = 15
EXPECTED_VERSE_RECORD_COUNT = 5337
EXPECTED_IDS = [
    "EST-SWETE", "JDT-SWETE", "TOB-SWETE", "1MA-SWETE", "2MA-SWETE",
    "WIS-SWETE", "SIR-SWETE", "BAR-SWETE", "EPJ-SWETE",
    "SUS-OG-SWETE", "SUS-TH-SWETE", "DAN-OG-SWETE", "DAN-TH-SWETE",
    "BEL-OG-SWETE", "BEL-TH-SWETE",
]
PRIMARY_IDS = {
    "EST-SWETE", "JDT-SWETE", "TOB-SWETE", "1MA-SWETE", "2MA-SWETE",
    "WIS-SWETE", "SIR-SWETE", "BAR-SWETE", "EPJ-SWETE",
    "SUS-TH-SWETE", "DAN-TH-SWETE", "BEL-TH-SWETE",
}
PARALLEL_IDS = {"SUS-OG-SWETE", "DAN-OG-SWETE", "BEL-OG-SWETE"}
SUPPORTED_BOOKS = {"EST", "JDT", "TOB", "1MA", "2MA", "WIS", "SIR", "BAR", "DAN"}
HEX40 = re.compile(r"^[0-9a-f]{40}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")


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


def source_registry_entry() -> dict:
    registry = load(SOURCES_MANIFEST)
    for row in registry.get("sources") or []:
        if row.get("id") == "first1kgreek-swete":
            return row
    raise ValidationError("First1KGreek/Swete source registry entry missing")


def witness_path(root: Path, witness_id: str) -> Path:
    return root / ISOLATED_ROOT / "witnesses" / f"{witness_id}.json"


def scan_forbidden(value, path: str = "root") -> None:
    forbidden = {
        "gloss", "glosses", "lemma", "lemmata", "morphology", "transliteration",
        "english_text", "english_scripture", "english_scripture_text",
    }
    if isinstance(value, dict):
        for key, item in value.items():
            if str(key).lower() in forbidden:
                raise ValidationError(f"unapproved field {key!r} found at {path}")
            scan_forbidden(item, f"{path}.{key}")
    elif isinstance(value, list):
        for index, item in enumerate(value):
            scan_forbidden(item, f"{path}[{index}]")


def refs(payload: dict) -> set[tuple[str | None, str]]:
    return {
        (row.get("source_chapter"), str(row.get("source_verse")))
        for row in (payload.get("verses") or [])
    }


def validate_static_registry() -> None:
    source = source_registry_entry()
    need(source.get("status") == "approved-for-production-ingestion", "First1KGreek registry status is not production-approved")
    need(source.get("production_import_allowed") is True, "First1KGreek production import is not enabled")
    need(source.get("license_verified") is True and source.get("source_inventory_verified") is True, "First1KGreek verification flags incomplete")
    need(source.get("license") == "CC BY-SA 4.0", "First1KGreek licence changed")
    need(source.get("share_alike") is True and source.get("isolation_required") is True, "First1KGreek ShareAlike isolation changed")
    need((source.get("pin") or {}).get("value") == SOURCE_COMMIT, "First1KGreek immutable source pin changed")
    acceptance = source.get("owner_acceptance") or {}
    need(acceptance.get("phase") == "Old Testament Expansion Phase 1B", "First1KGreek acceptance phase missing")
    need(acceptance.get("merge_commit") == PHASE1B_ACCEPTANCE_MERGE, "First1KGreek acceptance merge changed")
    integrity = source.get("integrity") or {}
    need(integrity.get("status") == "verified-by-phase1b-source-lock", "First1KGreek integrity status incomplete")
    need(integrity.get("witness_count") == EXPECTED_WITNESS_COUNT, "First1KGreek registry witness count changed")
    need(integrity.get("source_verse_record_count") == EXPECTED_VERSE_RECORD_COUNT, "First1KGreek registry verse evidence changed")


def validate_package(root: Path) -> None:
    need(root.exists(), f"production package missing: {root}")
    entries = sorted(path.name for path in root.iterdir())
    need(entries == ["manifest.json", "sharealike", "versification-map.json"], f"unexpected production package entries: {entries}")

    manifest = load(root / "manifest.json")
    need(manifest.get("corpus_id") == CORPUS_ID, "unexpected OT Greek corpus id")
    need(manifest.get("corpus_version") == CORPUS_VERSION, "unexpected OT Greek corpus version")
    need(manifest.get("production_enabled") is True, "OT Greek production package is disabled")
    need(manifest.get("language") == "grc", "OT Greek production language changed")

    acceptance = manifest.get("phase1b_acceptance") or {}
    need(acceptance.get("merge_commit") == PHASE1B_ACCEPTANCE_MERGE, "Phase 1B acceptance merge mismatch")
    need(acceptance.get("witness_count") == EXPECTED_WITNESS_COUNT, "accepted witness count changed")
    need(acceptance.get("source_verse_record_count") == EXPECTED_VERSE_RECORD_COUNT, "accepted source verse count changed")
    need(acceptance.get("primary_integration_witness_count") == len(PRIMARY_IDS), "primary witness count changed")
    need(acceptance.get("parallel_witness_count") == len(PARALLEL_IDS), "parallel witness count changed")

    source = manifest.get("source") or {}
    need(source.get("repository") == "OpenGreekAndLatin/First1KGreek", "unexpected production source repository")
    need(source.get("commit") == SOURCE_COMMIT and source.get("septuagint_tree_sha") == SOURCE_TREE, "production source pin mismatch")
    need(source.get("license") == "CC BY-SA 4.0", "production source licence changed")
    need(source.get("share_alike") is True and source.get("isolation_required") is True, "production ShareAlike isolation missing")

    partition = manifest.get("partition") or {}
    need(partition.get("path") == ISOLATED_ROOT, "production partition path changed")
    need(partition.get("license") == "CC BY-SA 4.0", "production partition licence changed")
    need(partition.get("share_alike") is True and partition.get("isolation_required") is True, "production partition isolation missing")

    mapping = manifest.get("mapping") or {}
    need(mapping.get("path") == "versification-map.json", "production mapping path changed")
    need(mapping.get("source_boundaries_preserved") is True, "source-boundary preservation lost")
    need(mapping.get("one_to_one_only_when_verified") is True, "one-to-one safety rule lost")
    need(mapping.get("component_range_allowed") is True, "component-range mapping rule lost")
    need(mapping.get("parallel_witnesses_do_not_replace_primary") is True, "parallel witness safety rule lost")
    need(mapping.get("fabricate_verse_boundaries") is False, "verse-boundary fabrication enabled")

    canonical_mapping = load(VERSIFICATION_MAP)
    packaged_mapping = load(root / "versification-map.json")
    need(packaged_mapping == canonical_mapping, "packaged Catholic versification map differs from accepted Phase 1B mapping")

    witness_meta = manifest.get("witnesses") or {}
    need(set(witness_meta.get("primary_integration") or []) == PRIMARY_IDS, "production primary witness inventory changed")
    need(set(witness_meta.get("parallel") or []) == PARALLEL_IDS, "production parallel witness inventory changed")
    need(set(witness_meta.get("supported_canonical_books") or []) == SUPPORTED_BOOKS, "production canonical book scope changed")

    derived = manifest.get("derived_layers") or {}
    need(set(derived) == {"glosses", "lemmata", "morphology", "transliteration"}, "unexpected derived-layer manifest keys")
    need(all(value is False for value in derived.values()), "unapproved OT Greek derived layer enabled")

    runtime = manifest.get("runtime_contract") or {}
    need(runtime.get("daniel_primary_witness") == "Theodotion", "Daniel primary witness changed")
    need(runtime.get("daniel_parallel_witness") == "Old Greek", "Daniel parallel witness changed")
    need(runtime.get("daniel_14_component_range_only") is True, "Daniel 14 component-range safety lost")
    need(runtime.get("bel_source_verse_count") == 36 and runtime.get("bel_douay_rheims_verse_count") == 42, "Bel/DRA verse-count difference lost")

    serving = manifest.get("serving_contract") or {}
    for key in (
        "source_surfaces_preserved",
        "english_corpus_unchanged",
        "oshb_corpus_unchanged",
        "greek_nt_corpus_unchanged",
        "no_english_scripture_text_in_package",
        "no_fabricated_gloss_or_linguistic_annotation",
    ):
        need(serving.get(key) is True, f"serving contract missing: {key}")

    isolated = root / ISOLATED_ROOT
    phase_manifest = load(isolated / "manifest.json")
    need(phase_manifest.get("production_enabled") is False and phase_manifest.get("production_import_allowed") is False, "embedded Phase 1B evidence must remain validation-only")
    need(phase_manifest.get("witness_count") == EXPECTED_WITNESS_COUNT, "embedded witness count changed")
    need(phase_manifest.get("verse_record_count") == EXPECTED_VERSE_RECORD_COUNT, "embedded verse count changed")
    phase_source = phase_manifest.get("source") or {}
    need(phase_source.get("commit") == SOURCE_COMMIT and phase_source.get("septuagint_tree_sha") == SOURCE_TREE, "embedded source pin changed")
    need(phase_source.get("license") == "CC BY-SA 4.0", "embedded source licence changed")

    files = sorted((isolated / "witnesses").glob("*.json"))
    need(len(files) == EXPECTED_WITNESS_COUNT, "production witness file count changed")
    need([path.stem for path in files] == sorted(EXPECTED_IDS), "production witness file inventory changed")

    lock = load(SOURCE_LOCK)
    locked = {str(row.get("id")): row for row in (lock.get("witnesses") or [])}
    total = 0
    payloads: dict[str, dict] = {}
    for witness_id in EXPECTED_IDS:
        payload = load(witness_path(root, witness_id))
        payloads[witness_id] = payload
        need(payload.get("production_enabled") is False, f"{witness_id}: embedded evidence unexpectedly enabled")
        need(payload.get("partition") == "sharealike-first1kgreek-swete", f"{witness_id}: partition marker changed")
        need(payload.get("license") == "CC BY-SA 4.0", f"{witness_id}: licence changed")
        need(payload.get("share_alike") is True and payload.get("isolation_required") is True, f"{witness_id}: isolation metadata incomplete")
        src = payload.get("source") or {}
        need(src.get("commit") == SOURCE_COMMIT, f"{witness_id}: source commit changed")
        need(src.get("metadata_git_blob_sha1") == locked[witness_id]["metadata_git_blob_sha1"], f"{witness_id}: metadata blob changed")
        need(src.get("text_git_blob_sha1") == locked[witness_id]["text_git_blob_sha1"], f"{witness_id}: text blob changed")
        need(HEX40.fullmatch(str(src.get("metadata_git_blob_sha1") or "")) is not None, f"{witness_id}: invalid metadata blob")
        need(HEX40.fullmatch(str(src.get("text_git_blob_sha1") or "")) is not None, f"{witness_id}: invalid text blob")
        need(HEX64.fullmatch(str(src.get("metadata_sha256") or "")) is not None, f"{witness_id}: metadata SHA-256 missing")
        need(HEX64.fullmatch(str(src.get("text_sha256") or "")) is not None, f"{witness_id}: text SHA-256 missing")
        need(src.get("per_file_license_verified") is True, f"{witness_id}: per-file licence verification missing")
        verses = payload.get("verses") or []
        need(verses, f"{witness_id}: no source verses")
        need(all(str(row.get("surface") or "").strip() for row in verses), f"{witness_id}: empty source surface")
        source_refs = [(row.get("source_chapter"), str(row.get("source_verse"))) for row in verses]
        need(len(source_refs) == len(set(source_refs)), f"{witness_id}: duplicate source reference")
        scan_forbidden(verses, witness_id)
        total += len(verses)
    need(total == EXPECTED_VERSE_RECORD_COUNT, f"production source verse total changed: {total}")

    epj_refs = refs(payloads["EPJ-SWETE"])
    need(len(payloads["EPJ-SWETE"].get("verses") or []) == 72, "Epistle of Jeremiah source count changed")
    need(any(verse == "1" for _, verse in epj_refs) and any(verse == "72" for _, verse in epj_refs), "Epistle of Jeremiah 1-72 evidence missing")

    sus_refs = refs(payloads["SUS-TH-SWETE"])
    need(len(payloads["SUS-TH-SWETE"].get("verses") or []) == 64, "Theodotion Susanna source count changed")
    need(("1", "1") in sus_refs and ("1", "64") in sus_refs, "Theodotion Susanna 1:1-64 evidence missing")

    bel_refs = refs(payloads["BEL-TH-SWETE"])
    need(len(payloads["BEL-TH-SWETE"].get("verses") or []) == 36, "Theodotion Bel source count changed")
    need(("1", "1") in bel_refs and ("1", "36") in bel_refs, "Theodotion Bel 1:1-36 evidence missing")

    dan_refs = refs(payloads["DAN-TH-SWETE"])
    need(("3", "24") in dan_refs and ("3", "90") in dan_refs, "Theodotion Daniel 3:24-90 evidence missing")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    validate_static_registry()
    validate_package(args.root.resolve())
    print(
        "Logos OT Greek production validation passed: 15 accepted witnesses / 5337 source verse records; "
        "CC BY-SA 4.0 isolated; Catholic mapping preserved; no fabricated derived layers"
    )


if __name__ == "__main__":
    try:
        main()
    except ValidationError as exc:
        raise SystemExit(str(exc))
