#!/usr/bin/env python3
"""Build the validation-only Logos Old Testament Phase 1B Greek witness corpus."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
PHASE_ROOT = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "old_testament_phase1b"
LOCK_PATH = PHASE_ROOT / "source-lock.json"
MAP_PATH = PHASE_ROOT / "versification-map.json"
DEFAULT_OUTPUT = ROOT / "build" / "logos-old-testament-phase1b"
HEX40 = re.compile(r"^[0-9a-f]{40}$")
WHITESPACE = re.compile(r"\s+")
EXCLUDED_SURFACE_TAGS = {"note", "pb", "milestone", "head"}


class BuildError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read {path}: {exc}") from exc


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def request_bytes(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": "Mercy-Logos-OT-Phase1B/1.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=60) as response:
                return response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    raise BuildError(f"failed to download {url}: {last_error}")


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def fetch_locked_tree(repo: str, tree_sha: str) -> dict[str, str]:
    if not HEX40.fullmatch(tree_sha):
        raise BuildError("invalid First1KGreek tree SHA")
    raw = request_bytes(f"https://api.github.com/repos/{repo}/git/trees/{tree_sha}?recursive=1")
    try:
        data = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot decode locked First1KGreek tree: {exc}") from exc
    if data.get("sha") != tree_sha or data.get("truncated"):
        raise BuildError("locked First1KGreek tree identity/truncation failure")
    inventory: dict[str, str] = {}
    for row in data.get("tree") or []:
        if row.get("type") != "blob":
            continue
        path = str(row.get("path") or "")
        sha = str(row.get("sha") or "")
        if path and HEX40.fullmatch(sha):
            inventory[path] = sha
    return inventory


def relative_to_tree(path: str, tree_root: str) -> str:
    prefix = tree_root.rstrip("/") + "/"
    if not path.startswith(prefix):
        raise BuildError(f"source path escapes locked Septuagint tree: {path}")
    return path[len(prefix):]


def download_pinned(repo: str, commit: str, path: str, expected_blob: str) -> tuple[bytes, str]:
    if not HEX40.fullmatch(commit) or not HEX40.fullmatch(expected_blob):
        raise BuildError(f"invalid immutable source pin for {path}")
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{quote(path, safe='/')}"
    payload = request_bytes(url)
    actual = git_blob_sha1(payload)
    if actual != expected_blob:
        raise BuildError(f"Git blob mismatch for {path}: expected {expected_blob}, got {actual}")
    return payload, hashlib.sha256(payload).hexdigest()


def verify_metadata(payload: bytes, witness: dict) -> None:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise BuildError(f"{witness['id']}: invalid CTS metadata XML: {exc}") from exc
    work_urn = str(witness["work_urn"])
    edition_urn = str(witness["edition_urn"])
    if root.attrib.get("urn") != work_urn:
        raise BuildError(f"{witness['id']}: CTS work URN mismatch")
    editions = [node.attrib.get("urn") for node in root.iter() if local_name(node.tag) == "edition"]
    if edition_urn not in editions:
        raise BuildError(f"{witness['id']}: selected CTS edition is absent from metadata")
    if witness.get("rejected_alternate_edition") == edition_urn:
        raise BuildError(f"{witness['id']}: rejected alternate edition was selected")


def verify_tei_license(root: ET.Element, witness_id: str, target: str) -> None:
    licenses = [node for node in root.iter() if local_name(node.tag) in {"licence", "license"}]
    for node in licenses:
        text = " ".join("".join(node.itertext()).split())
        if node.attrib.get("target") == target and "Attribution-ShareAlike 4.0" in text:
            return
    raise BuildError(f"{witness_id}: per-file CC BY-SA 4.0 licence declaration missing")


def surface_text(node: ET.Element) -> str:
    pieces: list[str] = []

    def walk(current: ET.Element) -> None:
        if current.text:
            pieces.append(current.text)
        for child in list(current):
            if local_name(child.tag) not in EXCLUDED_SURFACE_TAGS:
                walk(child)
            if child.tail:
                pieces.append(child.tail)

    walk(node)
    return WHITESPACE.sub(" ", "".join(pieces)).strip()


def parse_tei(payload: bytes, witness: dict, license_target: str) -> tuple[list[dict], dict]:
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise BuildError(f"{witness['id']}: invalid TEI XML: {exc}") from exc
    verify_tei_license(root, str(witness["id"]), license_target)
    edition_urn = str(witness["edition_urn"])
    edition_nodes = [
        node for node in root.iter()
        if local_name(node.tag) == "div" and node.attrib.get("type") == "edition" and node.attrib.get("n") == edition_urn
    ]
    if len(edition_nodes) != 1:
        raise BuildError(f"{witness['id']}: expected exactly one selected TEI edition div")

    verses: list[dict] = []
    seen: set[tuple[str | None, str]] = set()

    def walk(node: ET.Element, chapter: str | None = None) -> None:
        if local_name(node.tag) == "div" and node.attrib.get("subtype") == "chapter":
            chapter = str(node.attrib.get("n") or "")
            if not chapter:
                raise BuildError(f"{witness['id']}: chapter without source n")
        if local_name(node.tag) == "div" and node.attrib.get("subtype") == "verse":
            verse = str(node.attrib.get("n") or "")
            if not verse:
                raise BuildError(f"{witness['id']}: verse without source n")
            key = (chapter, verse)
            if key in seen:
                raise BuildError(f"{witness['id']}: duplicate source locus {chapter}:{verse}")
            seen.add(key)
            text = surface_text(node)
            if not text:
                raise BuildError(f"{witness['id']}: empty surface at source locus {chapter}:{verse}")
            source_ref = f"{chapter}:{verse}" if chapter is not None else verse
            verses.append({"source_chapter": chapter, "source_verse": verse, "source_reference": source_ref, "surface": text})
            return
        for child in list(node):
            walk(child, chapter)

    walk(edition_nodes[0])
    if not verses:
        raise BuildError(f"{witness['id']}: no TEI verse divisions parsed")
    chapter_values = {v["source_chapter"] for v in verses if v["source_chapter"] is not None}
    return verses, {"verse_count": len(verses), "chapter_count": len(chapter_values)}


def mapping_for(witness_id: str, mapping: dict) -> dict:
    for row in mapping.get("identity_books") or []:
        if row.get("witness_id") == witness_id:
            return row
    for row in (mapping.get("baruch") or {}).get("segments") or []:
        if row.get("witness_id") == witness_id:
            return row
    esther = mapping.get("esther") or {}
    if esther.get("witness_id") == witness_id:
        return esther
    daniel = mapping.get("daniel") or {}
    for row in daniel.get("primary_segments") or []:
        if row.get("witness_id") == witness_id:
            return row
    for row in daniel.get("parallel_segments") or []:
        if row.get("witness_id") == witness_id:
            return row
    raise BuildError(f"missing versification mapping for {witness_id}")


def build(output: Path) -> dict:
    lock = load_json(LOCK_PATH)
    mapping = load_json(MAP_PATH)
    if lock.get("production_enabled") is not False or lock.get("production_import_allowed") is not False:
        raise BuildError("Phase 1B must remain validation-only")
    witnesses = lock.get("witnesses") or []
    if len(witnesses) != 15:
        raise BuildError(f"Phase 1B requires exactly 15 source witnesses, got {len(witnesses)}")
    source = lock.get("source") or {}
    repo = str(source.get("repository") or "")
    commit = str(source.get("commit") or "")
    tree_sha = str(source.get("septuagint_tree_sha") or "")
    tree_root = str(source.get("septuagint_path") or "")
    if repo != "OpenGreekAndLatin/First1KGreek" or source.get("license") != "CC BY-SA 4.0":
        raise BuildError("unexpected Phase 1B source or licence")
    inventory = fetch_locked_tree(repo, tree_sha)

    if output.exists():
        shutil.rmtree(output)
    isolated = output / str(source["output_partition"])
    witness_dir = isolated / "witnesses"
    witness_dir.mkdir(parents=True, exist_ok=True)

    stats: list[dict] = []
    total_verses = 0
    total_chapters = 0
    for witness in witnesses:
        wid = str(witness["id"])
        metadata_path = str(witness["metadata_path"])
        text_path = str(witness["text_path"])
        metadata_blob = str(witness["metadata_git_blob_sha1"])
        text_blob = str(witness["text_git_blob_sha1"])
        for path, expected in ((metadata_path, metadata_blob), (text_path, text_blob)):
            rel = relative_to_tree(path, tree_root)
            actual_tree_blob = inventory.get(rel)
            if actual_tree_blob != expected:
                raise BuildError(f"{wid}: locked tree blob mismatch for {path}; expected {expected}, got {actual_tree_blob}")

        metadata_payload, metadata_sha256 = download_pinned(repo, commit, metadata_path, metadata_blob)
        text_payload, text_sha256 = download_pinned(repo, commit, text_path, text_blob)
        verify_metadata(metadata_payload, witness)
        verses, counts = parse_tei(text_payload, witness, str(source["license_target"]))
        canonical_mapping = mapping_for(wid, mapping)
        payload = {
            "schema_version": 1,
            "phase": "Old Testament Expansion Phase 1B",
            "production_enabled": False,
            "partition": "sharealike-first1kgreek-swete",
            "license": "CC BY-SA 4.0",
            "share_alike": True,
            "isolation_required": True,
            "witness_id": wid,
            "name": witness["name"],
            "canonical_scope": witness["canonical_scope"],
            "witness_role": witness["witness_role"],
            "source": {
                "repository": repo,
                "commit": commit,
                "work_urn": witness["work_urn"],
                "edition_urn": witness["edition_urn"],
                "metadata_path": metadata_path,
                "metadata_git_blob_sha1": metadata_blob,
                "metadata_sha256": metadata_sha256,
                "text_path": text_path,
                "text_git_blob_sha1": text_blob,
                "text_sha256": text_sha256,
                "per_file_license_verified": True,
            },
            "canonical_mapping": canonical_mapping,
            "surface_policy": {
                "unicode_normalization": "none",
                "whitespace": "collapsed-layout-whitespace",
                "excluded_editorial_tags": sorted(EXCLUDED_SURFACE_TAGS),
                "glosses": False,
                "lemmata": False,
                "morphology": False,
                "transliteration": False,
            },
            "verses": verses,
        }
        write_json(witness_dir / f"{wid}.json", payload)
        row = {
            "witness_id": wid,
            "canonical_scope": witness["canonical_scope"],
            "witness_role": witness["witness_role"],
            "chapter_count": counts["chapter_count"],
            "verse_count": counts["verse_count"],
            "metadata_git_blob_sha1": metadata_blob,
            "metadata_sha256": metadata_sha256,
            "text_git_blob_sha1": text_blob,
            "text_sha256": text_sha256,
        }
        stats.append(row)
        total_chapters += counts["chapter_count"]
        total_verses += counts["verse_count"]

    manifest = {
        "schema_version": 1,
        "phase": "Old Testament Expansion Phase 1B",
        "production_enabled": False,
        "production_import_allowed": False,
        "owner_acceptance_required": True,
        "source": {
            "id": source["id"],
            "repository": repo,
            "commit": commit,
            "septuagint_tree_sha": tree_sha,
            "license": "CC BY-SA 4.0",
            "share_alike": True,
            "isolation_required": True,
            "attribution": source["attribution"],
        },
        "isolation": {
            "root": source["output_partition"],
            "english_corpus_unchanged": True,
            "oshb_corpus_unchanged": True,
            "greek_nt_corpus_unchanged": True,
            "contains_english_scripture_text": False,
        },
        "derived_layers": {"glosses": False, "lemmata": False, "morphology": False, "transliteration": False},
        "witness_count": len(stats),
        "chapter_container_count": total_chapters,
        "verse_record_count": total_verses,
        "witnesses": stats,
    }
    write_json(isolated / "manifest.json", manifest)
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = build(args.output.resolve())
    print(
        "Logos OT Phase 1B validation corpus built: "
        f"{manifest['witness_count']} witnesses, {manifest['verse_record_count']} source verse records; "
        "CC BY-SA 4.0 isolated; production disabled"
    )


if __name__ == "__main__":
    try:
        main()
    except BuildError as exc:
        raise SystemExit(str(exc))
