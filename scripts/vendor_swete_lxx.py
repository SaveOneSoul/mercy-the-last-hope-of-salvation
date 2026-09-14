#!/usr/bin/env python3
"""Vendor the pinned Swete/First1KGreek source layer after its source lock is complete."""

from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "lxx-swete-inventory.json"
OUTPUT_DIR = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_swete_lxx"
RAW_BASE = "https://raw.githubusercontent.com/OpenGreekAndLatin/First1KGreek"


class SourceLockError(RuntimeError):
    pass


def load_inventory() -> dict:
    try:
        return json.loads(INVENTORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SourceLockError(f"cannot read source lock: {exc}") from exc


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def validate_lock(inventory: dict) -> list[str]:
    errors: list[str] = []
    units = inventory.get("units") or []
    missing = inventory.get("missing_source_units") or []
    required = int(inventory.get("required_source_unit_count") or 0)
    verified = int(inventory.get("verified_source_unit_count") or 0)

    if inventory.get("source_id") != "first1kgreek-swete":
        errors.append("unexpected source_id")
    if inventory.get("license") != "CC BY-SA 4.0":
        errors.append("unexpected licence")
    if inventory.get("share_alike") is not True or inventory.get("isolation_required") is not True:
        errors.append("ShareAlike isolation flags are required")
    if inventory.get("checksum_type") != "git_blob_sha1":
        errors.append("checksum_type must be git_blob_sha1")
    if len(units) != verified:
        errors.append(f"verified_source_unit_count={verified} but units={len(units)}")
    if len(units) + len(missing) != required:
        errors.append("verified + missing source units does not equal required_source_unit_count")

    seen_paths: set[str] = set()
    for unit in units:
        path = str(unit.get("path") or "")
        checksum = str(unit.get("git_blob_sha1") or "")
        if not path.startswith("data/tlg0527/") or not path.endswith(".xml"):
            errors.append(f"invalid source path: {path!r}")
        if path in seen_paths:
            errors.append(f"duplicate source path: {path}")
        seen_paths.add(path)
        if len(checksum) != 40 or any(ch not in "0123456789abcdef" for ch in checksum):
            errors.append(f"invalid Git blob checksum for {path}")
        edition = str(unit.get("edition") or "")
        if not edition:
            errors.append(f"missing edition for {path}")

    complete = inventory.get("lock_complete") is True
    if complete and missing:
        errors.append("lock_complete=true while missing_source_units is non-empty")
    if not complete and not missing:
        errors.append("lock_complete=false without a recorded blocker")
    return errors


def check_lock(inventory: dict) -> int:
    errors = validate_lock(inventory)
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1

    if inventory.get("lock_complete") is not True:
        missing = inventory.get("missing_source_units") or []
        print(
            "LXX source lock is structurally valid but BLOCKED: "
            f"{len(inventory.get('units') or [])}/{inventory.get('required_source_unit_count')} "
            "required source units are checksum-locked."
        )
        for row in missing:
            print(f"BLOCKER: {','.join(row.get('book_ids') or [])} / {row.get('work_id')}: {row.get('reason')}")
        return 0

    print(
        "LXX source lock is complete: "
        f"{len(inventory.get('units') or [])} checksum-locked source units."
    )
    return 0


def fetch_unit(inventory: dict, unit: dict) -> tuple[bytes, str]:
    commit = inventory["upstream_commit"]
    path = unit["path"]
    url = f"{RAW_BASE}/{commit}/{path}"
    request = urllib.request.Request(url, headers={"User-Agent": "Mercy-Logos-LXX-Vendor/1.0"})
    with urllib.request.urlopen(request, timeout=45) as response:
        data = response.read()

    actual_blob = git_blob_sha1(data)
    expected_blob = unit["git_blob_sha1"]
    if actual_blob != expected_blob:
        raise SourceLockError(
            f"Git blob checksum mismatch for {path}: expected {expected_blob}, got {actual_blob}"
        )

    try:
        ET.fromstring(data)
    except ET.ParseError as exc:
        raise SourceLockError(f"invalid XML for {path}: {exc}") from exc

    return data, hashlib.sha256(data).hexdigest()


def vendor(inventory: dict) -> None:
    errors = validate_lock(inventory)
    if errors:
        raise SourceLockError("; ".join(errors))
    if inventory.get("lock_complete") is not True:
        blockers = ", ".join(
            f"{'/'.join(row.get('book_ids') or [])}:{row.get('work_id')}"
            for row in inventory.get("missing_source_units") or []
        )
        raise SourceLockError(
            "refusing to vendor Greek Catholic OT: source lock is incomplete"
            + (f" ({blockers})" if blockers else "")
        )

    temp_dir = OUTPUT_DIR.with_name(OUTPUT_DIR.name + ".tmp")
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)
    source_dir = temp_dir / "source_xml"
    source_dir.mkdir()

    vendored: list[dict] = []
    try:
        for unit in inventory["units"]:
            data, sha256 = fetch_unit(inventory, unit)
            filename = Path(unit["path"]).name
            output_path = source_dir / filename
            output_path.write_bytes(data)
            vendored.append(
                {
                    "book_ids": unit["book_ids"],
                    "work_id": unit["work_id"],
                    "edition": unit["edition"],
                    "edition_urn": f"urn:cts:greekLit:tlg0527.{unit['work_id']}.{unit['edition']}",
                    "source_path": unit["path"],
                    "vendored_path": f"source_xml/{filename}",
                    "git_blob_sha1": unit["git_blob_sha1"],
                    "sha256": sha256,
                }
            )

        manifest = {
            "schema_version": 1,
            "corpus_id": "grc_swete_lxx",
            "language": "grc",
            "source_id": inventory["source_id"],
            "upstream_repository": inventory["upstream_repository"],
            "upstream_commit": inventory["upstream_commit"],
            "license": inventory["license"],
            "share_alike": True,
            "isolation_required": True,
            "source_unit_count": len(vendored),
            "units": vendored,
        }
        (temp_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (temp_dir / "NOTICE.txt").write_text(
            "OpenGreekAndLatin First1KGreek / Swete source layer.\n"
            "Licensed CC BY-SA 4.0. Preserve attribution and ShareAlike obligations.\n"
            f"Pinned upstream commit: {inventory['upstream_commit']}\n",
            encoding="utf-8",
        )

        if OUTPUT_DIR.exists():
            shutil.rmtree(OUTPUT_DIR)
        temp_dir.replace(OUTPUT_DIR)
    except Exception:
        if temp_dir.exists():
            shutil.rmtree(temp_dir)
        raise

    print(f"Vendored {len(vendored)} locked LXX source XML files into {OUTPUT_DIR.relative_to(ROOT)}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--check-lock",
        action="store_true",
        help="validate the source-lock manifest without downloading or writing corpus data",
    )
    args = parser.parse_args()
    inventory = load_inventory()

    if args.check_lock:
        return check_lock(inventory)

    try:
        vendor(inventory)
    except SourceLockError as exc:
        print(f"LXX vendor blocked: {exc}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
