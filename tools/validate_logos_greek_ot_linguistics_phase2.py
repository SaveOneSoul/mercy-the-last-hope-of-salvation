#!/usr/bin/env python3
"""Validate the Greek OT linguistic Phase 2 source/provenance gate."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERLINEAR = ROOT / "cloud-backend" / "app" / "logos_interlinear"
SOURCES = INTERLINEAR / "sources-manifest.json"
BOOKS = INTERLINEAR / "books.json"
LOCK = INTERLINEAR / "greek_ot_linguistics_phase2" / "source-lock.json"

EXPECTED_SOURCE_ID = "lxx-morph-rahlfs"
EXPECTED_COMMIT = "c91f6b1e8fb3ba37df701e6ae31f675ace71a2b2"
EXPECTED_LICENSE = "CC BY 4.0"
REQUIRED_FIELDS = {"surface", "lemma", "parsing", "pos", "provenance", "confidence"}
REQUIRED_POLICIES = {
    "source_text_immutable",
    "no_fabricated_linguistics",
    "no_fabricated_token_boundaries",
    "no_cross_edition_relabeling",
    "exact_revision_required",
    "source_inventory_required_before_import",
    "per_file_checksum_required_before_import",
    "verse_alignment_required_before_attachment",
    "token_alignment_required_before_attachment",
    "lexical_mismatch_must_block_attachment",
    "edition_provenance_required_in_runtime",
    "scholarly_quality_caveat_required",
}


def fail(message: str) -> None:
    raise SystemExit(f"Greek OT linguistics Phase 2 validation failed: {message}")


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {path.relative_to(ROOT)}: {exc}")


def main() -> int:
    sources = load(SOURCES).get("sources") or []
    source = next((row for row in sources if row.get("id") == EXPECTED_SOURCE_ID), None)
    if not source:
        fail("lxx-morph source record is missing")
    if source.get("production_import_allowed") is not False:
        fail("candidate Rahlfs morphology must remain production-blocked at the source gate")
    if source.get("license") != EXPECTED_LICENSE or source.get("license_verified") is not True:
        fail("candidate Rahlfs morphology license gate changed")
    if source.get("source_inventory_verified") is not True:
        fail("pinned lxx-morph source inventory must be verified")
    pin = source.get("pin") or {}
    if pin.get("type") != "git-commit" or pin.get("value") != EXPECTED_COMMIT:
        fail("candidate Rahlfs morphology immutable revision changed")
    edition = source.get("edition") or {}
    if edition.get("text") != "Rahlfs Septuagint (1935)":
        fail("Rahlfs edition identity is missing")
    if edition.get("relationship_to_installed_greek_surface") != "separate-witness":
        fail("Rahlfs morphology must remain a separate witness at this gate")
    reported = source.get("reported_scope") or {}
    if int(reported.get("greek_old_testament_book_count") or 0) != 59:
        fail("reported upstream lxx-morph book scope changed")
    if set(reported.get("fields") or []) != REQUIRED_FIELDS:
        fail("reported lxx-morph linguistic field contract changed")

    lock = load(LOCK)
    if lock.get("status") != "source-gate":
        fail("phase status must remain source-gate")
    production = lock.get("production") or {}
    if production.get("enabled") is not False:
        fail("production cannot be enabled before source inventory and alignment validation")
    lock_source = lock.get("source") or {}
    if lock_source.get("source_id") != EXPECTED_SOURCE_ID or lock_source.get("commit") != EXPECTED_COMMIT:
        fail("phase source lock does not match source manifest")
    if lock_source.get("license") != EXPECTED_LICENSE:
        fail("phase source license does not match source manifest")
    if lock_source.get("text_edition") != "Rahlfs Septuagint (1935)":
        fail("phase source edition must remain Rahlfs 1935")
    if lock_source.get("inventory_status") != "verified-pinned-archive":
        fail("pinned archive inventory verification is missing")
    if lock_source.get("archive_sha256") != "b3c4861f47152ea8fab7d3ed78d807a9a0c2b35d07f2cb64fa9deefd6ac960a9":
        fail("pinned archive SHA-256 changed")
    if int(lock_source.get("archive_file_count") or 0) != 5966:
        fail("pinned archive file inventory count changed")

    books = load(BOOKS).get("books") or []
    expected_ot = [(int(row["order"]), str(row["id"]), str(row["name"])) for row in books if row.get("testament") == "OT"]
    target = lock.get("target") or {}
    target_rows = target.get("books") or []
    actual_ot = [(int(row["order"]), str(row["book_id"]), str(row["name"])) for row in target_rows]
    if len(expected_ot) != 46 or int(target.get("catholic_ot_book_count") or 0) != 46:
        fail("Catholic OT scope must contain exactly 46 books")
    if actual_ot != expected_ot:
        fail("phase target books must exactly match the ordered Catholic OT canon")
    if any(row.get("testament") == "NT" for row in target_rows):
        fail("Greek OT linguistic phase cannot include NT books")

    installed = lock.get("installed_surface_witnesses") or {}
    if installed.get("primary") != "first1kgreek-swete":
        fail("installed primary Greek OT surface witness changed")
    if installed.get("ecclesiastes_fallback") != "open-greek-ecclesiastes":
        fail("installed Ecclesiastes Greek surface witness changed")
    if "separate" not in str(installed.get("policy") or "").lower():
        fail("cross-edition separate-witness policy is missing")

    policies = lock.get("integrity_policy") or {}
    missing = sorted(key for key in REQUIRED_POLICIES if policies.get(key) is not True)
    if missing:
        fail(f"required integrity policies are not enabled: {missing}")

    gates = lock.get("acceptance_gates") or []
    if len(gates) < 9:
        fail("acceptance gate inventory is incomplete")
    if not str(lock.get("quality_note") or "").strip():
        fail("scholarly quality caveat is required")

    print(
        "Greek OT linguistics Phase 2 source gate passed: "
        "46 Catholic OT books targeted; Rahlfs/lxx-morph pinned as a separate CC BY 4.0 linguistic witness; "
        "production import remains blocked pending immutable inventory and deterministic cross-edition alignment"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
