#!/usr/bin/env python3
"""Validate the generated 46-book Rahlfs/lxx-morph Greek OT linguistic corpus."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "build" / "logos-greek-ot-linguistics-phase2"
BOOKS_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "books.json"
CORPUS_ID = "grc_ot_rahlfs_lxx_morph"
COMMIT = "c91f6b1e8fb3ba37df701e6ae31f675ace71a2b2"
ARCHIVE_SHA256 = "b3c4861f47152ea8fab7d3ed78d807a9a0c2b35d07f2cb64fa9deefd6ac960a9"
REQUIRED_TOKEN_FIELDS = {
    "position",
    "surface",
    "lemma",
    "morphology",
    "part_of_speech",
    "confidence",
    "provenance_source",
    "reasoning",
}


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--require-production", action="store_true")
    args = parser.parse_args()
    corpus = args.root.resolve()
    manifest = load(corpus / "manifest.json")

    require(manifest.get("corpus_id") == CORPUS_ID, "unexpected corpus id")
    expected_status = "production-installed" if args.require_production else "validation-only"
    require(manifest.get("status") == expected_status, f"unexpected corpus status: {manifest.get('status')}")
    require(manifest.get("production_enabled") is args.require_production, "production_enabled does not match validation mode")
    require(int(manifest.get("book_count") or 0) == 46, "generated corpus must contain 46 Catholic OT books")
    require(int(manifest.get("verse_record_count") or 0) > 0, "generated corpus has no verse records")
    require(int(manifest.get("token_count") or 0) > 0, "generated corpus has no word tokens")

    source = manifest.get("source") or {}
    require(source.get("source_id") == "lxx-morph-rahlfs", "linguistic source id changed")
    require(source.get("commit") == COMMIT, "source commit changed")
    require(source.get("archive_sha256") == ARCHIVE_SHA256, "source archive SHA-256 changed")
    require(source.get("license") == "CC BY 4.0", "data license changed")
    require(source.get("license_path") == "LICENSE-DATA", "license evidence path changed")
    require(source.get("data_path") == "db/seeds/lxx_morph/", "morphology data path changed")
    require(source.get("text_edition") == "Rahlfs Septuagint (1935)", "Rahlfs edition identity changed")

    runtime = manifest.get("runtime_contract") or {}
    for key in (
        "source_native_references_preserved",
        "source_token_order_preserved",
        "cross_edition_relabeling_forbidden",
        "no_fabricated_linguistics",
        "no_glosses_added",
        "no_transliteration_added",
    ):
        require(runtime.get(key) is True, f"runtime safety contract {key} must be true")
    require(runtime.get("automatic_attachment_to_swete") is False, "automatic Swete attachment must remain disabled")
    require(runtime.get("automatic_canonical_remapping") is False, "automatic canonical remapping must remain disabled")

    canon = load(BOOKS_PATH).get("books") or []
    expected = [row for row in canon if row.get("testament") == "OT"]
    require(len(expected) == 46, "canonical registry no longer contains 46 OT books")
    expected_ids = [str(row["id"]) for row in expected]

    rows = manifest.get("books") or []
    require([str(row.get("book_id")) for row in rows] == expected_ids, "manifest book order/scope differs from Catholic OT canon")
    inventory = manifest.get("source_file_inventory") or {}
    require(len(inventory) >= 48, "source file inventory is unexpectedly incomplete")
    for filename, meta in inventory.items():
        require(str(filename).endswith(".json"), f"source inventory contains non-final file {filename}")
        require(str(meta.get("path") or "").startswith("db/seeds/lxx_morph/"), f"{filename}: source path escaped data root")
        sha = str(meta.get("sha256") or "")
        require(len(sha) == 64 and all(ch in "0123456789abcdef" for ch in sha), f"{filename}: invalid SHA-256")
        require(int(meta.get("full_file_verse_count") or 0) > 0, f"{filename}: no source verses")

    total_verses = 0
    total_tokens = 0
    for meta in expected:
        book_id = str(meta["id"])
        payload = load(corpus / "books" / f"{book_id}.json")
        require(payload.get("corpus_id") == CORPUS_ID, f"{book_id}: corpus id changed")
        require(payload.get("book_id") == book_id, f"{book_id}: book id changed")
        require(payload.get("book") == meta.get("name"), f"{book_id}: canonical book label changed")
        require(payload.get("status") == expected_status, f"{book_id}: unexpected status")
        require(payload.get("production_enabled") is args.require_production, f"{book_id}: production flag does not match validation mode")
        require(payload.get("text_edition") == "Rahlfs Septuagint (1935)", f"{book_id}: edition identity changed")
        require(payload.get("linguistic_source") == "lxx-morph-rahlfs", f"{book_id}: linguistic source changed")
        require(payload.get("license") == "CC BY 4.0", f"{book_id}: license changed")
        policy = payload.get("cross_edition_policy") or {}
        require(policy.get("relationship") == "separate-witness", f"{book_id}: must remain a separate Rahlfs witness")
        require(policy.get("automatic_attachment_to_installed_surface") is False, f"{book_id}: automatic surface attachment enabled")
        require(policy.get("canonical_versification_remapping") is False, f"{book_id}: automatic remapping enabled")

        components = payload.get("components") or []
        verses = payload.get("verses") or []
        require(components and verses, f"{book_id}: components/verses missing")
        require(int(payload.get("verse_count") or 0) == len(verses), f"{book_id}: verse count mismatch")
        seen: set[tuple[str, str]] = set()
        book_tokens = 0
        for row in verses:
            component = str(row.get("component") or "")
            source_ref = str(row.get("source_ref") or "")
            require(component and source_ref, f"{book_id}: source component/reference missing")
            key = (component, source_ref)
            require(key not in seen, f"{book_id}: duplicate source row {key}")
            seen.add(key)
            tokens = row.get("tokens") or []
            require(tokens, f"{book_id} {source_ref}: no tokens")
            for index, token in enumerate(tokens, start=1):
                require(REQUIRED_TOKEN_FIELDS <= set(token), f"{book_id} {source_ref}: token fields incomplete")
                require(int(token.get("position") or 0) == index, f"{book_id} {source_ref}: token order changed")
                for field in ("surface", "lemma", "part_of_speech", "provenance_source", "reasoning"):
                    require(str(token.get(field) or "").strip(), f"{book_id} {source_ref}: empty {field}")
                require("gloss" not in token, f"{book_id} {source_ref}: importer fabricated a gloss field")
                require("transliteration" not in token, f"{book_id} {source_ref}: importer fabricated a transliteration field")
            book_tokens += len(tokens)
        require(int(payload.get("token_count") or 0) == book_tokens, f"{book_id}: token count mismatch")
        total_verses += len(verses)
        total_tokens += book_tokens

    require(total_verses == int(manifest["verse_record_count"]), "manifest verse total mismatch")
    require(total_tokens == int(manifest["token_count"]), "manifest token total mismatch")
    require(str(manifest.get("quality_note") or "").strip(), "quality caveat is missing")

    print(
        "Greek OT linguistic validation corpus passed: "
        f"46 Catholic OT books, {total_verses} source verse records, {total_tokens} word tokens; "
        "Rahlfs/lxx-morph provenance preserved as a separate witness"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        raise SystemExit(f"Greek OT linguistic corpus validation failed: {exc}") from exc
