#!/usr/bin/env python3
"""Validate the source-locked TAGNT John 7:53-8:11 linguistic fallback."""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "cloud-backend/app/logos_interlinear/greek_nt_linguistics_phase2a/source-lock.json"
REGISTRY = ROOT / "cloud-backend/app/logos_interlinear/sources-manifest.json"
DEFAULT_ROOT = ROOT / "cloud-backend/app/logos_corpus/grc_tagnt_john_fallback"
EXPECTED_COMMIT = "ae39711d7843b2902d54993e432de9c12d6a4b9a"
EXPECTED_BLOB = "705c1bc1cf752e013efcef99b8d9a3b7853bf843"
EXPECTED_REFS = ["7:53","8:1","8:2","8:3","8:4","8:5","8:6","8:7","8:8","8:9","8:10","8:11"]
HEX64 = re.compile(r"^[0-9a-f]{64}$")


def fail(message: str) -> None:
    raise SystemExit(f"TAGNT John fallback validation failed: {message}")


def load(path: Path) -> dict:
    if not path.exists():
        fail(f"missing {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot parse {path}: {exc}")


def validate_static() -> None:
    lock = load(LOCK)
    registry = load(REGISTRY)
    if lock.get("phase") != "Greek NT Linguistics Completion Phase 2A":
        fail("unexpected phase")
    source = lock.get("source") or {}
    if source.get("repository") != "STEPBible/STEPBible-Data":
        fail("TAGNT repository changed")
    if source.get("commit") != EXPECTED_COMMIT or source.get("blob_sha1") != EXPECTED_BLOB:
        fail("TAGNT immutable source pin changed")
    if source.get("license") != "CC BY 4.0":
        fail("TAGNT license must remain CC BY 4.0")
    coverage = lock.get("coverage") or {}
    if coverage.get("references") != EXPECTED_REFS:
        fail("John fallback reference inventory changed")
    if int(coverage.get("expected_token_rows") or 0) != 198:
        fail("expected TAGNT token-row count changed")
    if coverage.get("source_tokenization_preserved") is not True:
        fail("source tokenization must be preserved")
    if coverage.get("cross_edition_token_identity_claimed") is not False:
        fail("must not claim TAGNT/SBLGNT token identity")
    integrity = lock.get("integrity") or {}
    if integrity.get("no_fabricated_linguistics") is not True:
        fail("no-fabrication gate missing")
    if integrity.get("do_not_overwrite_morphgnt") is not True:
        fail("MorphGNT overwrite prohibition missing")

    registry_index = {row.get("id"): row for row in (registry.get("sources") or [])}
    step = registry_index.get("stepbible-data") or {}
    if step.get("production_import_allowed") is not True or step.get("license") != "CC BY 4.0":
        fail("STEPBible registry source is not production-approved CC BY 4.0")
    if (step.get("pin") or {}).get("value") != EXPECTED_COMMIT:
        fail("STEPBible global registry pin differs from Phase 2A source lock")
    if "TAGNT" not in (step.get("datasets") or []):
        fail("TAGNT is not in the approved STEPBible dataset inventory")
    if "TAGOT" not in (step.get("excluded_datasets") or {}):
        fail("unfinished TAGOT exclusion gate is missing")


def validate_generated(root: Path) -> None:
    manifest = load(root / "manifest.json")
    payload = load(root / "JHN-7-53--8-11.json")
    if manifest.get("corpus_id") != "grc_tagnt_john_fallback":
        fail("unexpected corpus id")
    if manifest.get("production_enabled") is not True:
        fail("supplemental corpus is not production-enabled")
    if manifest.get("references") != EXPECTED_REFS:
        fail("manifest reference inventory mismatch")
    if int(manifest.get("verse_count") or 0) != 12 or int(manifest.get("token_row_count") or 0) != 198:
        fail("manifest coverage count mismatch")
    if manifest.get("cross_edition_token_identity_claimed") is not False:
        fail("manifest falsely claims cross-edition token identity")
    if manifest.get("no_fabricated_linguistics") is not True:
        fail("manifest no-fabrication gate missing")

    source = manifest.get("source") or {}
    if source.get("commit") != EXPECTED_COMMIT or source.get("blob_sha1") != EXPECTED_BLOB:
        fail("generated source pin mismatch")
    if source.get("license") != "CC BY 4.0":
        fail("generated source license mismatch")
    if not HEX64.fullmatch(str(source.get("sha256") or "")):
        fail("generated source SHA-256 missing")

    if payload.get("alignment_policy", {}).get("cross_edition_token_identity_claimed") is not False:
        fail("payload falsely claims token identity")
    verses = payload.get("verses") or {}
    if list(verses) != EXPECTED_REFS:
        fail("payload reference inventory mismatch")
    total = 0
    for ref in EXPECTED_REFS:
        rows = verses.get(ref) or []
        if not rows:
            fail(f"{ref}: no TAGNT linguistic rows")
        positions = [int(row.get("position") or 0) for row in rows]
        if positions != list(range(1, len(rows) + 1)):
            fail(f"{ref}: token positions are not contiguous")
        for row in rows:
            for field in ("source_token_ref", "surface", "strongs", "part_of_speech_morphology", "lemma", "editions"):
                if not str(row.get(field) or "").strip():
                    fail(f"{ref}: token missing {field}")
        total += len(rows)
    if total != 198:
        fail(f"observed TAGNT token rows {total}, expected 198")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--static-only", action="store_true")
    args = parser.parse_args()
    validate_static()
    if not args.static_only:
        validate_generated(args.root.resolve())
    print("TAGNT John fallback validation passed: 12 verses, 198 source linguistic rows, CC BY 4.0 pin and no-fabrication boundary preserved")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
