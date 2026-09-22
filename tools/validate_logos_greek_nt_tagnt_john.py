#!/usr/bin/env python3
"""Validate the production TAGNT John 7:53–8:11 linguistic supplement."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_nt_tagnt_john_pa"
EXPECTED_REFS = ["7:53"] + [f"8:{i}" for i in range(1, 12)]
CORPUS_ID = "grc_nt_tagnt_john_pa"
COMMIT = "ae39711d7843b2902d54993e432de9c12d6a4b9a"
BLOB = "705c1bc1cf752e013efcef99b8d9a3b7853bf843"


class ValidationError(RuntimeError):
    pass


def require(value: bool, message: str) -> None:
    if not value:
        raise ValidationError(message)


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    manifest = load(args.root.resolve() / "manifest.json")

    require(manifest.get("corpus_id") == CORPUS_ID, "unexpected corpus id")
    require(manifest.get("production_enabled") is True, "TAGNT supplement must be production-enabled")
    require(manifest.get("status") == "production-installed", "TAGNT supplement status changed")
    require(manifest.get("book_id") == "JHN", "TAGNT supplement must be John-only")
    require(int(manifest.get("verse_count") or 0) == 12, "TAGNT supplement must contain exactly 12 verses")
    require(int(manifest.get("token_count") or 0) > 0, "TAGNT supplement has no token rows")

    source = manifest.get("source") or {}
    require(source.get("source_id") == "stepbible-data", "TAGNT source id changed")
    require(source.get("dataset") == "TAGNT", "TAGNT dataset id changed")
    require(source.get("commit") == COMMIT, "TAGNT source commit changed")
    require(source.get("git_blob_sha1") == BLOB, "TAGNT source blob changed")
    require(source.get("license") == "CC BY 4.0", "TAGNT license changed")

    policy = manifest.get("witness_policy") or {}
    require(policy.get("relationship_to_sblgnt") == "supplemental-parallel-linguistic-witness", "TAGNT/SBL witness relationship changed")
    require(policy.get("automatic_attachment_to_sblgnt") is False, "TAGNT may not auto-attach to SBLGNT")
    require(policy.get("automatic_reconstruction_of_sblgnt") is False, "TAGNT may not reconstruct SBLGNT")
    require(policy.get("tagnt_is_amalgamated") is True, "TAGNT amalgamated-witness disclosure is missing")
    for key in ("edition_membership_preserved_per_token", "word_type_preserved_per_token", "variant_fields_preserved_per_token", "no_fabricated_pos_labels", "no_fabricated_lemma", "no_fabricated_morphology"):
        require(policy.get(key) is True, f"TAGNT policy {key} changed")

    verses = manifest.get("verses") or []
    require([str(row.get("reference")) for row in verses] == EXPECTED_REFS, "TAGNT verse inventory/order changed")
    total = 0
    for verse in verses:
        ref = str(verse.get("reference"))
        require(verse.get("canonical_reference") == f"John {ref}", f"{ref}: canonical label changed")
        tokens = verse.get("tokens") or []
        require(tokens, f"{ref}: no TAGNT token rows")
        positions = []
        for token in tokens:
            positions.append(int(token.get("position") or 0))
            for key in ("raw_reference", "word_type", "surface", "greek_raw", "dstrongs_grammar", "dictionary_raw", "editions"):
                require(str(token.get(key) or "").strip(), f"{ref}: token has empty {key}")
            require(token.get("part_of_speech_codes"), f"{ref}: source grammar yielded no POS code")
            require(token.get("dictionary_forms"), f"{ref}: source dictionary field yielded no form")
        require(len(positions) == len(set(positions)), f"{ref}: duplicate token positions")
        require(positions == sorted(positions), f"{ref}: token positions are not ordered")
        require(int(verse.get("token_count") or 0) == len(tokens), f"{ref}: token count mismatch")
        total += len(tokens)
    require(total == int(manifest.get("token_count") or 0), "manifest token total mismatch")

    print(f"TAGNT John supplement validation passed: 12 verses / {total} source token rows; supplemental witness provenance preserved")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        raise SystemExit(f"TAGNT John supplement validation failed: {exc}") from exc
