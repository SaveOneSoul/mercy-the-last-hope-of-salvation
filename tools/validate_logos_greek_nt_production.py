#!/usr/bin/env python3
"""Validate the promoted Greek NT production package and its license partitions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_sblgnt_morphgnt"
EXPECTED_PHASE1_MERGE = "7ee1b88676f5b19a92a5080abee389232ee56382"
EXPECTED_SBL_COMMIT = "c4d241a9c1c479a55b989ba35a4976c1d0b8052c"
EXPECTED_MORPH_COMMIT = "aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d"
EXPECTED_BOOK_IDS = [
    "MAT", "MRK", "LUK", "JHN", "ACT", "ROM", "1CO", "2CO", "GAL",
    "EPH", "PHP", "COL", "1TH", "2TH", "1TI", "2TI", "TIT", "PHM",
    "HEB", "JAS", "1PE", "2PE", "1JN", "2JN", "3JN", "JUD", "REV",
]


def fail(message: str) -> None:
    raise SystemExit(f"Greek NT production validation failed: {message}")


def load(path: Path) -> dict:
    if not path.exists():
        fail(f"missing {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot parse {path}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()

    manifest = load(root / "manifest.json")
    phase1 = load(root / "phase1" / "manifest.json")

    if manifest.get("corpus_id") != "grc_sblgnt_morphgnt":
        fail("unexpected corpus id")
    if manifest.get("status") != "production-installed" or manifest.get("production_enabled") is not True:
        fail("production manifest is not enabled")
    if manifest.get("language") != "grc":
        fail("production corpus language must be Greek")

    accepted = manifest.get("phase1_acceptance") or {}
    if accepted.get("merge_commit") != EXPECTED_PHASE1_MERGE:
        fail("Phase 1 acceptance merge commit changed")
    for key, expected in (
        ("book_count", 27),
        ("chapter_count", 260),
        ("verse_count", 7939),
        ("morphology_coverage_verse_count", 7927),
        ("annotation_gap_verse_count", 12),
        ("lexical_mismatch_count", 0),
    ):
        if int(accepted.get(key) or 0) != expected:
            fail(f"production acceptance {key} changed")

    if phase1.get("status") != "validation-generated" or phase1.get("production_enabled") is not False:
        fail("embedded Phase 1 evidence must remain validation-generated and non-production")
    if int(phase1.get("book_count") or 0) != 27:
        fail("embedded Phase 1 book count changed")
    if int(phase1.get("chapter_count") or 0) != 260:
        fail("embedded Phase 1 chapter count changed")
    if int(phase1.get("verse_count") or 0) != 7939:
        fail("embedded Phase 1 verse count changed")
    if int(phase1.get("token_count") or 0) != 137741:
        fail("embedded Phase 1 token count changed")
    if int(phase1.get("morphology_coverage_verse_count") or 0) != 7927:
        fail("embedded Phase 1 morphology coverage changed")
    if int(phase1.get("annotation_gap_verse_count") or 0) != 12:
        fail("embedded Phase 1 annotation-gap count changed")
    if int(phase1.get("lexical_mismatch_count") or 0) != 0:
        fail("embedded Phase 1 lexical mismatch count is non-zero")

    sources = manifest.get("sources") or {}
    surface = sources.get("surface") or {}
    linguistics = sources.get("linguistics") or {}
    if surface.get("commit") != EXPECTED_SBL_COMMIT or surface.get("license") != "CC BY 4.0":
        fail("SBLGNT production source pin/license changed")
    if linguistics.get("commit") != EXPECTED_MORPH_COMMIT or linguistics.get("license") != "CC BY-SA 3.0":
        fail("MorphGNT production source pin/license changed")
    if linguistics.get("share_alike") is not True or linguistics.get("isolation_required") is not True:
        fail("MorphGNT ShareAlike isolation is not enforced")

    partitions = manifest.get("partitions") or {}
    if set(partitions) != {"surface", "linguistics", "alignment"}:
        fail("production package must expose three separate partitions")
    if partitions["surface"].get("path") != "phase1/surface":
        fail("surface partition path changed")
    if partitions["linguistics"].get("path") != "phase1/linguistics":
        fail("linguistics partition path changed")
    if partitions["linguistics"].get("share_alike") is not True:
        fail("linguistics partition lost ShareAlike marker")
    if partitions["alignment"].get("contains_source_text") is not False:
        fail("alignment partition leaked source text")

    gap = manifest.get("annotation_gap_policy") or {}
    if gap.get("verse_count") != 12 or gap.get("fabricate_morphology") is not False:
        fail("annotation-gap policy changed")
    if gap.get("surface_text_preserved") is not True:
        fail("annotation-gap policy must preserve SBLGNT surface text")

    if (manifest.get("gloss_layer") or {}).get("installed") is not False:
        fail("production package must not invent a gloss layer")
    contract = manifest.get("serving_contract") or {}
    if contract.get("surface_and_linguistics_remain_separate") is not True:
        fail("serving contract must preserve license partitions")
    if contract.get("english_corpus_unchanged") is not True:
        fail("serving contract must leave the English corpus unchanged")

    for layer in ("surface", "linguistics", "alignment"):
        layer_dir = root / "phase1" / layer
        files = sorted(path.stem for path in layer_dir.glob("*.json"))
        if files != sorted(EXPECTED_BOOK_IDS):
            fail(f"{layer} partition does not contain exactly the 27 expected NT books")

    john_surface = load(root / "phase1" / "surface" / "JHN.json")
    john_ling = load(root / "phase1" / "linguistics" / "JHN.json")
    if not john_surface["chapters"]["1"]["1"]["tokens"]:
        fail("John 1:1 Greek surface tokens missing")
    if john_ling["chapters"]["7"]["53"].get("annotation_status") != "unavailable-in-pinned-morphgnt":
        fail("John 7:53 source-locked morphology gap missing")
    for verse in range(1, 12):
        row = john_ling["chapters"]["8"][str(verse)]
        if row.get("annotation_status") != "unavailable-in-pinned-morphgnt" or row.get("tokens") != []:
            fail(f"John 8:{verse} annotation gap must remain explicit and empty")

    print(
        "Greek NT production validation passed: 27 books, 260 chapters, 7939 verses, "
        "137741 SBLGNT tokens, 7927 MorphGNT-covered verses, 12 explicit source gaps, "
        "license partitions preserved"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
