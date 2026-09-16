#!/usr/bin/env python3
"""Promote accepted OT Phase 1B Greek witnesses into a production package.

The accepted Phase 1B importer remains the sole authority for source extraction.
This script rebuilds and validates that evidence, then copies it without
reinterpreting source verse boundaries. CC BY-SA 4.0 material remains isolated
under its ShareAlike partition and Catholic/Douay-Rheims mapping stays metadata.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PHASE1B_SCRIPT = ROOT / "scripts" / "vendor_old_testament_phase1b.py"
PHASE1B_VALIDATOR = ROOT / "tools" / "validate_logos_old_testament_phase1b.py"
SOURCE_LOCK = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "old_testament_phase1b" / "source-lock.json"
VERSIFICATION_MAP = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "old_testament_phase1b" / "versification-map.json"
DEFAULT_OUTPUT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_ot_catholic_swete"
PHASE1B_ACCEPTANCE_MERGE = "22ad0019355d6924592d3c6b5176624e6fd4c866"
CORPUS_VERSION = "2026.09.16-swete-catholic-greek-15"
ISOLATED_ROOT = "sharealike/first1kgreek_swete_cc-by-sa-4.0"
EXPECTED_WITNESS_COUNT = 15
EXPECTED_VERSE_RECORD_COUNT = 5337
PRIMARY_WITNESSES = [
    "EST-SWETE",
    "JDT-SWETE",
    "TOB-SWETE",
    "1MA-SWETE",
    "2MA-SWETE",
    "WIS-SWETE",
    "SIR-SWETE",
    "BAR-SWETE",
    "EPJ-SWETE",
    "SUS-TH-SWETE",
    "DAN-TH-SWETE",
    "BEL-TH-SWETE",
]
PARALLEL_WITNESSES = ["SUS-OG-SWETE", "DAN-OG-SWETE", "BEL-OG-SWETE"]
SUPPORTED_BOOKS = ["EST", "JDT", "TOB", "1MA", "2MA", "WIS", "SIR", "BAR", "DAN"]


class ProductionBuildError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ProductionBuildError(f"cannot read {path}: {exc}") from exc


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def run_checked(*args: str) -> None:
    completed = subprocess.run(args, cwd=ROOT, check=False)
    if completed.returncode != 0:
        raise ProductionBuildError(f"command failed with exit code {completed.returncode}: {' '.join(args)}")


def production_manifest(phase1b: dict, lock: dict, mapping: dict) -> dict:
    source = lock.get("source") or {}
    return {
        "schema_version": 1,
        "corpus_id": "grc_ot_catholic_swete",
        "corpus_version": CORPUS_VERSION,
        "status": "production-installed",
        "production_enabled": True,
        "language": "grc",
        "scope": "Catholic Old Testament Greek deuterocanonical books and additions — 15 preserved witnesses",
        "phase1b_acceptance": {
            "validated_phase": "Old Testament Expansion Phase 1B",
            "merge_commit": PHASE1B_ACCEPTANCE_MERGE,
            "witness_count": phase1b.get("witness_count"),
            "source_verse_record_count": phase1b.get("verse_record_count"),
            "primary_integration_witness_count": len(PRIMARY_WITNESSES),
            "parallel_witness_count": len(PARALLEL_WITNESSES),
        },
        "source": {
            "id": source.get("id"),
            "repository": source.get("repository"),
            "commit": source.get("commit"),
            "septuagint_tree_sha": source.get("septuagint_tree_sha"),
            "license": source.get("license"),
            "license_target": source.get("license_target"),
            "share_alike": True,
            "isolation_required": True,
            "attribution": source.get("attribution"),
        },
        "partition": {
            "path": ISOLATED_ROOT,
            "license": "CC BY-SA 4.0",
            "share_alike": True,
            "isolation_required": True,
            "contains": ["source Greek verse surfaces", "source provenance", "witness metadata"],
        },
        "mapping": {
            "path": "versification-map.json",
            "canonical_reference_system": (mapping.get("mapping_policy") or {}).get("canonical_reference_system"),
            "source_reference_system": (mapping.get("mapping_policy") or {}).get("source_reference_system"),
            "source_boundaries_preserved": True,
            "one_to_one_only_when_verified": True,
            "component_range_allowed": True,
            "parallel_witnesses_do_not_replace_primary": True,
            "fabricate_verse_boundaries": False,
        },
        "witnesses": {
            "primary_integration": PRIMARY_WITNESSES,
            "parallel": PARALLEL_WITNESSES,
            "supported_canonical_books": SUPPORTED_BOOKS,
        },
        "derived_layers": {
            "glosses": False,
            "lemmata": False,
            "morphology": False,
            "transliteration": False,
        },
        "runtime_contract": {
            "exact_identity_mapping_books": ["TOB", "JDT", "1MA", "2MA", "WIS", "SIR"],
            "baruch_1_5_identity": True,
            "baruch_6_epistle_of_jeremiah": True,
            "esther_component_range_mapping": True,
            "daniel_primary_witness": "Theodotion",
            "daniel_parallel_witness": "Old Greek",
            "daniel_3_24_90_exact_source_range": True,
            "daniel_13_susanna_exact_source_verse_numbering": True,
            "daniel_14_component_range_only": True,
            "bel_source_verse_count": 36,
            "bel_douay_rheims_verse_count": 42,
        },
        "serving_contract": {
            "source_surfaces_preserved": True,
            "english_corpus_unchanged": True,
            "oshb_corpus_unchanged": True,
            "greek_nt_corpus_unchanged": True,
            "no_english_scripture_text_in_package": True,
            "no_fabricated_gloss_or_linguistic_annotation": True,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    target = args.output.resolve()
    if target == ROOT.resolve():
        raise ProductionBuildError("refusing to use repository root as output directory")

    lock = load_json(SOURCE_LOCK)
    mapping = load_json(VERSIFICATION_MAP)
    if lock.get("phase") != "Old Testament Expansion Phase 1B":
        raise ProductionBuildError("unexpected Phase 1B source lock")
    if lock.get("production_enabled") is not False or lock.get("production_import_allowed") is not False:
        raise ProductionBuildError("accepted Phase 1B evidence must remain validation-only")
    if mapping.get("production_enabled") is not False:
        raise ProductionBuildError("accepted Phase 1B versification map must remain validation-only metadata")

    with tempfile.TemporaryDirectory(prefix="logos-ot-greek-production-") as tmp:
        phase1b_dir = Path(tmp) / "phase1b"
        run_checked(sys.executable, str(PHASE1B_SCRIPT), "--output", str(phase1b_dir))
        run_checked(sys.executable, str(PHASE1B_VALIDATOR), "--generated", str(phase1b_dir))
        phase1b_manifest = load_json(phase1b_dir / ISOLATED_ROOT / "manifest.json")

        if int(phase1b_manifest.get("witness_count") or 0) != EXPECTED_WITNESS_COUNT:
            raise ProductionBuildError("validated Phase 1B witness count changed")
        if int(phase1b_manifest.get("verse_record_count") or 0) != EXPECTED_VERSE_RECORD_COUNT:
            raise ProductionBuildError("validated Phase 1B source verse total changed")
        if phase1b_manifest.get("production_enabled") is not False:
            raise ProductionBuildError("Phase 1B evidence unexpectedly became production-enabled")

        source_root = phase1b_dir / "sharealike"
        if not source_root.exists():
            raise ProductionBuildError("validated ShareAlike partition is missing")

        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(source_root, target / "sharealike")
        shutil.copy2(VERSIFICATION_MAP, target / "versification-map.json")
        write_json(target / "manifest.json", production_manifest(phase1b_manifest, lock, mapping))

    print(
        "[OT Greek Production] packaged 15 accepted witnesses / 5337 source verse records; "
        "CC BY-SA 4.0 isolation and Catholic mapping metadata preserved"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProductionBuildError as exc:
        raise SystemExit(f"OT Greek production build failed: {exc}") from exc
