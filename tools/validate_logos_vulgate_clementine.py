#!/usr/bin/env python3
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "lat_vulgate_clementine"
EXPECTED_COMMIT = "f257a3559025c3f873b48a75019f53a9354ed7de"
EXPECTED_BLOB = "c0e65106383658fd914e90da4c82f2be48a0a762"


def fail(message: str) -> None:
    raise SystemExit(f"Clementine Vulgate validation failed: {message}")


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot read {path}: {exc}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()
    manifest = load(root / "manifest.json")
    if manifest.get("corpus_id") != "lat_vulgate_clementine" or manifest.get("production_enabled") is not True:
        fail("unexpected corpus identity or production flag")
    if int(manifest.get("book_count") or 0) != 73:
        fail("corpus must contain exactly 73 Catholic books")
    if int(manifest.get("chapter_count") or 0) < 1200 or int(manifest.get("verse_count") or 0) < 30000:
        fail("corpus totals are unexpectedly incomplete")
    source = manifest.get("source") or {}
    if source.get("repository") != "seven1m/open-bibles" or source.get("commit") != EXPECTED_COMMIT:
        fail("immutable upstream source pin changed")
    if source.get("git_blob_sha1") != EXPECTED_BLOB or not source.get("sha256"):
        fail("source integrity evidence is incomplete")
    if source.get("rights") != "public-domain" or source.get("license") != "Public Domain":
        fail("public-domain rights gate is missing")
    evidence = source.get("rights_evidence") or {}
    if evidence.get("git_blob_sha1") != "50caf5d5b86fb69471c1b849584cc476a7944df5" or not evidence.get("sha256"):
        fail("rights evidence is not immutably pinned")
    runtime = manifest.get("runtime_contract") or {}
    if runtime.get("local_only") is not True or runtime.get("automatic_versification_remapping") is not False:
        fail("runtime safety contract changed")
    derived = manifest.get("derived_layers") or {}
    if any(derived.get(key) is not False for key in ("lemma", "morphology", "gloss", "transliteration")):
        fail("unavailable Latin linguistic layers must remain disabled")

    rows = manifest.get("books") or []
    ids = [str(row.get("id") or "") for row in rows]
    if len(rows) != 73 or len(set(ids)) != 73 or any(not book_id for book_id in ids):
        fail("manifest book inventory is not exactly 73 unique ids")
    files = [path for path in root.glob("*.json") if path.name != "manifest.json"]
    if len(files) != 73:
        fail(f"expected 73 Latin book files, found {len(files)}")
    for row in rows:
        path = root / str(row.get("filename") or "")
        payload = load(path)
        if payload.get("corpus_id") != "lat_vulgate_clementine" or payload.get("book_id") != row.get("id"):
            fail(f"book identity mismatch in {path.name}")
        if not (payload.get("chapters") or {}):
            fail(f"{path.name} has no chapters")

    genesis = load(root / "gen.json")
    if ((genesis.get("chapters") or {}).get("1") or {}).get("1") != "In principio creavit Deus cælum et terram.":
        fail("Genesis 1:1 source sentinel changed")
    if not ((load(root / "rev.json").get("chapters") or {}).get("22") or {}).get("21"):
        fail("Revelation 22:21 source sentinel missing")

    print(
        "Clementine Vulgate validation passed: "
        f"{manifest['book_count']} books / {manifest['chapter_count']} chapters / {manifest['verse_count']} verses"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
