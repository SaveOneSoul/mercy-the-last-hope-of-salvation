#!/usr/bin/env python3
"""Promote the validated Greek NT Phase 1 build into a production package.

This script never reinterprets or rewrites source data. It first runs the
source-locked Phase 1 importer and validator, then copies that validated output
verbatim under a production package root and writes a small production manifest.
The SBLGNT surface layer and MorphGNT linguistic layer remain separate license
partitions.
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
PHASE1_SCRIPT = ROOT / "scripts" / "vendor_greek_nt_phase1.py"
PHASE1_VALIDATOR = ROOT / "tools" / "validate_logos_greek_nt_phase1.py"
SOURCE_LOCK = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "greek_nt_phase1" / "source-lock.json"
DEFAULT_OUTPUT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_sblgnt_morphgnt"
PHASE1_MERGE_COMMIT = "7ee1b88676f5b19a92a5080abee389232ee56382"
CORPUS_VERSION = "2026.09.16-sblgnt-morphgnt-27"


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


def production_manifest(phase1: dict, lock: dict) -> dict:
    return {
        "schema_version": 1,
        "corpus_id": "grc_sblgnt_morphgnt",
        "corpus_version": CORPUS_VERSION,
        "status": "production-installed",
        "production_enabled": True,
        "language": "grc",
        "scope": "New Testament — 27 books",
        "phase1_acceptance": {
            "validated_phase": "Greek NT Expansion Phase 1",
            "merge_commit": PHASE1_MERGE_COMMIT,
            "book_count": phase1.get("book_count"),
            "chapter_count": phase1.get("chapter_count"),
            "verse_count": phase1.get("verse_count"),
            "surface_token_count": phase1.get("token_count"),
            "morphology_coverage_verse_count": phase1.get("morphology_coverage_verse_count"),
            "annotation_gap_verse_count": phase1.get("annotation_gap_verse_count"),
            "lexical_mismatch_count": phase1.get("lexical_mismatch_count"),
        },
        "sources": {
            "surface": {
                "id": "sblgnt",
                "repository": lock["sources"]["sblgnt"]["repository"],
                "commit": lock["sources"]["sblgnt"]["commit"],
                "license": lock["sources"]["sblgnt"]["license"],
                "role": "Greek surface text",
            },
            "linguistics": {
                "id": "morphgnt-sblgnt",
                "repository": lock["sources"]["morphgnt"]["repository"],
                "commit": lock["sources"]["morphgnt"]["commit"],
                "license": lock["sources"]["morphgnt"]["license"],
                "role": "lemma, normalized form, POS and morphology",
                "share_alike": True,
                "isolation_required": True,
            },
        },
        "partitions": {
            "surface": {
                "path": "phase1/surface",
                "license": "CC BY 4.0",
                "contains": ["Greek surface text", "derived transliteration"],
            },
            "linguistics": {
                "path": "phase1/linguistics",
                "license": "CC BY-SA 3.0",
                "share_alike": True,
                "contains": ["MorphGNT source surface", "lemma", "normalized form", "POS", "morphology"],
            },
            "alignment": {
                "path": "phase1/alignment",
                "license": "project-generated metadata",
                "contains_source_text": False,
                "contains_linguistic_payload": False,
            },
        },
        "annotation_gap_policy": {
            "references": ["John 7:53", "John 8:1-11"],
            "verse_count": 12,
            "surface_text_preserved": True,
            "morphology_status": "unavailable-in-pinned-morphgnt",
            "fabricate_morphology": False,
        },
        "gloss_layer": {
            "installed": False,
            "reason": "No separately approved gloss source has been licensed and source-locked yet.",
        },
        "serving_contract": {
            "surface_and_linguistics_remain_separate": True,
            "join_key": "token id",
            "source_surfaces_preserved": True,
            "english_corpus_unchanged": True,
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
    if lock.get("phase") != "Greek NT Expansion Phase 1":
        raise ProductionBuildError("unexpected Phase 1 source lock")
    if lock.get("owner_acceptance", {}).get("accepted") is not True:
        raise ProductionBuildError("accepted interlinear foundation is not recorded")

    with tempfile.TemporaryDirectory(prefix="logos-greek-nt-production-") as tmp:
        phase1_dir = Path(tmp) / "phase1"
        run_checked(sys.executable, str(PHASE1_SCRIPT), "--output", str(phase1_dir))
        run_checked(sys.executable, str(PHASE1_VALIDATOR), "--generated", str(phase1_dir))
        phase1_manifest = load_json(phase1_dir / "manifest.json")

        if int(phase1_manifest.get("book_count") or 0) != 27:
            raise ProductionBuildError("validated Phase 1 output does not contain 27 books")
        if int(phase1_manifest.get("chapter_count") or 0) != 260:
            raise ProductionBuildError("validated Phase 1 output does not contain 260 chapters")
        if int(phase1_manifest.get("verse_count") or 0) != 7939:
            raise ProductionBuildError("validated Phase 1 verse count changed")
        if int(phase1_manifest.get("annotation_gap_verse_count") or 0) != 12:
            raise ProductionBuildError("expected MorphGNT annotation-gap count changed")
        if int(phase1_manifest.get("lexical_mismatch_count") or 0) != 0:
            raise ProductionBuildError("cannot promote a corpus with lexical mismatches")

        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)
        shutil.copytree(phase1_dir, target / "phase1")
        write_json(target / "manifest.json", production_manifest(phase1_manifest, lock))

    print(
        "[Greek NT Production] packaged 27 books, 260 chapters, 7939 verses; "
        "SBLGNT/MorphGNT license partitions preserved"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProductionBuildError as exc:
        raise SystemExit(f"Greek NT production build failed: {exc}") from exc
