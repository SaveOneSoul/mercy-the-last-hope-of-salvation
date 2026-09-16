#!/usr/bin/env python3
"""Promote accepted OT Phase 1A OSHB/WLC evidence into a production package.

The accepted Phase 1A importer remains the sole authority for source extraction.
This script rebuilds and validates that evidence, then copies the exact surface,
linguistics and alignment partitions without Unicode normalization or silent
Douay-Rheims versification remapping.
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
PHASE1A_SCRIPT = ROOT / "scripts" / "vendor_old_testament_phase1.py"
PHASE1A_VALIDATOR = ROOT / "tools" / "validate_logos_old_testament_phase1.py"
SOURCE_LOCK = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "old_testament_phase1" / "source-lock.json"
DEFAULT_OUTPUT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "heb_arc_oshb_wlc"
PHASE1A_ACCEPTANCE_MERGE = "c93507c2f2d7e6cec6540ac9a6f155dd6eefecc9"
CORPUS_VERSION = "2026.09.16-oshb-wlc-39"
EXPECTED = {
    "masoretic_book_witness_count": 39,
    "chapter_count": 929,
    "verse_count": 23213,
    "token_count": 305507,
    "hebrew_token_count": 300679,
    "aramaic_token_count": 4828,
    "alignment_mismatch_count": 0,
}


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


def production_manifest(phase1a: dict, lock: dict) -> dict:
    source = lock.get("source") or {}
    return {
        "schema_version": 1,
        "corpus_id": "heb_arc_oshb_wlc",
        "corpus_version": CORPUS_VERSION,
        "status": "production-installed",
        "production_enabled": True,
        "languages": ["he", "arc"],
        "scope": "39 Masoretic/Hebrew-Bible witnesses within the Catholic Old Testament",
        "phase1a_acceptance": {
            "validated_phase": "Old Testament Expansion Phase 1A",
            "merge_commit": PHASE1A_ACCEPTANCE_MERGE,
            **{key: int(phase1a.get(key) or 0) for key in EXPECTED},
        },
        "source": {
            "id": source.get("id"),
            "title": source.get("title"),
            "repository": source.get("repository"),
            "commit": source.get("commit"),
            "tree_sha": source.get("tree_sha"),
            "base_text": source.get("base_text"),
            "surface_rights": source.get("base_text_rights"),
            "linguistic_annotation_license": source.get("license"),
            "attribution": source.get("attribution"),
            "normalization_policy": source.get("normalization_policy"),
        },
        "partitions": {
            "root": "phase1a",
            "surface": {
                "path": "phase1a/surface",
                "rights": "Public Domain",
                "contains": ["source-script Hebrew/Aramaic token surfaces", "source OSIS verse ids"],
            },
            "linguistics": {
                "path": "phase1a/linguistics",
                "license": "CC BY 4.0",
                "attribution": "Open Scriptures Hebrew Bible Project",
                "contains": ["lemma", "morphology", "source word id", "language"],
            },
            "alignment": {
                "path": "phase1a/alignment",
                "mode": "same-source-exact-token-id",
                "mismatch_count": 0,
            },
        },
        "versification": {
            "canonical_reference_system": "Douay-Rheims Catholic 73-book corpus",
            "source_reference_system": "OSHB/WLC OSIS",
            "runtime_exact_identity_required": True,
            "automatic_remapping": False,
            "fabricate_verse_boundaries": False,
            "mismatched_chapters_blocked_until_explicit_mapping": True,
            "catholic_greek_additions_served_by_separate_ot_greek_corpus": True,
        },
        "derived_layers": {
            "glosses": False,
            "transliteration": False,
            "lemmata": True,
            "morphology": True,
            "lemma_morphology_are_source_annotations": True,
        },
        "runtime_contract": {
            "source_unicode_preserved_verbatim": True,
            "unicode_normalization_applied": False,
            "canonical_tokens_are_direct_verse_child_words_only": True,
            "nested_qere_variants_not_duplicated": True,
            "token_alignment_mismatch_count": 0,
            "supported_languages": ["he", "arc"],
            "exact_dra_source_verse_identity_checked_per_chapter": True,
        },
        "serving_contract": {
            "english_corpus_unchanged": True,
            "greek_nt_corpus_unchanged": True,
            "greek_ot_corpus_unchanged": True,
            "no_english_scripture_text_in_package": True,
            "no_fabricated_gloss_or_transliteration": True,
            "no_silent_mt_to_dra_verse_remapping": True,
        },
        "catholic_scope": {
            "masoretic_witnesses": 39,
            "esther_and_daniel": "Masoretic portions only in this package; Catholic Greek additions remain in grc_ot_catholic_swete",
            "deuterocanonical_greek_material": "Not duplicated here",
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
    if lock.get("phase") != "Old Testament Expansion Phase 1A":
        raise ProductionBuildError("unexpected Phase 1A source lock")
    if lock.get("production_enabled") is not False or lock.get("catholic_ot_complete") is not False:
        raise ProductionBuildError("accepted Phase 1A evidence must remain validation-only")

    with tempfile.TemporaryDirectory(prefix="logos-ot-semitic-production-") as tmp:
        phase1a_dir = Path(tmp) / "phase1a"
        run_checked(sys.executable, str(PHASE1A_SCRIPT), "--output", str(phase1a_dir))
        run_checked(sys.executable, str(PHASE1A_VALIDATOR), "--generated", str(phase1a_dir))
        phase1a = load_json(phase1a_dir / "manifest.json")
        for key, expected in EXPECTED.items():
            actual = int(phase1a.get(key) or 0)
            if actual != expected:
                raise ProductionBuildError(f"validated Phase 1A {key} changed: expected {expected}, got {actual}")
        if phase1a.get("production_enabled") is not False:
            raise ProductionBuildError("Phase 1A evidence unexpectedly became production-enabled")
        if phase1a.get("surface_normalization_applied") is not False:
            raise ProductionBuildError("Phase 1A source Unicode normalization marker changed")

        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(phase1a_dir, target / "phase1a")
        write_json(target / "manifest.json", production_manifest(phase1a, lock))

    print(
        "[OT Semitic Production] packaged 39 witnesses / 929 chapters / 23213 verses / "
        "305507 tokens; Hebrew/Aramaic source partitions preserved and silent DRA remapping disabled"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProductionBuildError as exc:
        raise SystemExit(f"OT Semitic production build failed: {exc}") from exc
