#!/usr/bin/env python3
"""Validate the First1KGreek/Swete Catholic OT source lock and activation gate."""

from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERLINEAR_DIR = ROOT / "cloud-backend" / "app" / "logos_interlinear"
INVENTORY_PATH = INTERLINEAR_DIR / "lxx-swete-inventory.json"
SOURCES_PATH = INTERLINEAR_DIR / "sources-manifest.json"
BOOKS_PATH = INTERLINEAR_DIR / "books.json"
VENDOR_PATH = ROOT / "scripts" / "vendor_swete_lxx.py"
GENERATED_DIR = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_swete_lxx"

SHA1_RE = re.compile(r"^[0-9a-f]{40}$")


def fail(message: str) -> None:
    raise SystemExit(f"LXX source-lock validation failed: {message}")


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {path.relative_to(ROOT)}: {exc}")


def main() -> int:
    inventory = load_json(INVENTORY_PATH)
    sources = load_json(SOURCES_PATH).get("sources") or []
    books = load_json(BOOKS_PATH).get("books") or []

    if not VENDOR_PATH.exists():
        fail("scripts/vendor_swete_lxx.py is missing")
    if inventory.get("source_id") != "first1kgreek-swete":
        fail("unexpected source_id")
    if inventory.get("license") != "CC BY-SA 4.0":
        fail("inventory must record CC BY-SA 4.0")
    if inventory.get("share_alike") is not True or inventory.get("isolation_required") is not True:
        fail("First1KGreek layer must remain ShareAlike-isolated")
    if inventory.get("checksum_type") != "git_blob_sha1":
        fail("inventory checksum_type must be git_blob_sha1")

    source = next((row for row in sources if row.get("id") == "first1kgreek-swete"), None)
    if source is None:
        fail("first1kgreek-swete source record is missing")
    if (source.get("pin") or {}).get("value") != inventory.get("upstream_commit"):
        fail("inventory commit does not match sources-manifest pin")
    if source.get("upstream_repository") != inventory.get("upstream_repository"):
        fail("inventory repository does not match sources-manifest")

    units = inventory.get("units") or []
    missing = inventory.get("missing_source_units") or []
    required = int(inventory.get("required_source_unit_count") or 0)
    verified = int(inventory.get("verified_source_unit_count") or 0)
    if verified != len(units):
        fail("verified_source_unit_count does not match units")
    if required != len(units) + len(missing):
        fail("required_source_unit_count does not equal verified + missing units")

    seen_paths: set[str] = set()
    seen_work_ids: set[str] = set()
    covered_books: set[str] = set()
    by_work: dict[str, dict] = {}
    for unit in units:
        work_id = str(unit.get("work_id") or "")
        path = str(unit.get("path") or "")
        edition = str(unit.get("edition") or "")
        checksum = str(unit.get("git_blob_sha1") or "")
        if not edition:
            fail(f"{work_id} is missing edition")
        if not work_id.startswith("tlg"):
            fail(f"invalid work id {work_id!r}")
        if path in seen_paths:
            fail(f"duplicate source path {path}")
        if work_id in seen_work_ids:
            fail(f"duplicate source work {work_id}")
        if not path.startswith(f"data/tlg0527/{work_id}/tlg0527.{work_id}.") or not path.endswith(".xml"):
            fail(f"{work_id} path is not canonical: {path}")
        if not path.endswith(f".{edition}.xml"):
            fail(f"{work_id} edition does not match its path")
        if not SHA1_RE.fullmatch(checksum):
            fail(f"{work_id} has invalid Git blob SHA-1")
        seen_paths.add(path)
        seen_work_ids.add(work_id)
        by_work[work_id] = unit
        covered_books.update(str(book_id) for book_id in unit.get("book_ids") or [])

    missing_books: set[str] = set()
    for row in missing:
        missing_books.update(str(book_id) for book_id in row.get("book_ids") or [])

    canonical_ot = {str(row["id"]) for row in books if row.get("testament") == "OT"}
    if len(canonical_ot) != 46:
        fail(f"expected 46 Catholic OT books, found {len(canonical_ot)}")
    if covered_books | missing_books != canonical_ot:
        absent = canonical_ot - (covered_books | missing_books)
        extra = (covered_books | missing_books) - canonical_ot
        fail(f"OT coverage mismatch; absent={sorted(absent)}, extra={sorted(extra)}")

    if set(by_work["tlg018"]["book_ids"]) != {"EZR", "NEH"}:
        fail("tlg018 must be the shared Ezra/Nehemiah source unit")
    if by_work["tlg019"]["book_ids"] != ["EST"]:
        fail("tlg019 must lock Greek Esther")
    if {work for work, row in by_work.items() if "BAR" in row["book_ids"]} != {"tlg050", "tlg052"}:
        fail("Baruch must lock tlg050 plus Letter of Jeremiah tlg052")
    if {work for work, row in by_work.items() if "DAN" in row["book_ids"]} != {"tlg057", "tlg058", "tlg059"}:
        fail("Daniel must use the locked Theodotion tlg057/tlg058/tlg059 source units")
    if not by_work["tlg034"]["path"].endswith("tlg0527.tlg034.1st1K-grc2.xml"):
        fail("Sirach must select the Swete grc2 edition, not Hart grc1")
    if not by_work["tlg048"]["path"].endswith("tlg0527.tlg048.1st1K-grc1.xml"):
        fail("Isaiah must select the Swete grc1 edition, not Ottley grc2")
    if {"tlg017", "tlg026", "tlg028", "tlg035", "tlg054", "tlg055", "tlg056"} & set(by_work):
        fail("excluded alternate/noncanonical works entered the primary source lock")

    complete = inventory.get("lock_complete") is True
    if complete:
        if missing:
            fail("lock_complete=true while blockers remain")
        if source.get("source_inventory_verified") is not True:
            fail("complete source lock requires source_inventory_verified=true")
        if source.get("production_import_allowed") is not True:
            fail("complete source lock requires production_import_allowed=true")
    else:
        if not missing:
            fail("incomplete lock must record at least one blocker")
        if source.get("source_inventory_verified") is not False:
            fail("incomplete lock must keep source_inventory_verified=false")
        if source.get("production_import_allowed") is not False:
            fail("incomplete lock must keep production_import_allowed=false")
        if GENERATED_DIR.exists():
            fail("generated Greek LXX corpus must not exist while source lock is incomplete")

    ecclesiastes = [
        row
        for row in missing
        if row.get("work_id") == "tlg030" and "ECC" in (row.get("book_ids") or [])
    ]
    if not complete and len(ecclesiastes) != 1:
        fail("current incomplete lock must explicitly record the Ecclesiastes/tlg030 blocker")

    print(
        "LXX source-lock validation passed: "
        f"{verified}/{required} required source units checksum-locked; "
        f"lock_complete={str(complete).lower()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
