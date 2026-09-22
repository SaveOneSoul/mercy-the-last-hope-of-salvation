#!/usr/bin/env python3
"""Inspect the pinned lxx-morph SourceHut archive without importing it.

This is a discovery gate for Greek OT Linguistics Phase 2. It intentionally
does not generate production corpus data. The output is designed for CI review
so the exact upstream inventory/schema can be pinned before an importer is
written.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import tarfile
import time
from pathlib import PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

COMMIT = "c91f6b1e8fb3ba37df701e6ae31f675ace71a2b2"
ARCHIVE_URL = f"https://git.sr.ht/~sethkush/lxx-morph/archive/{COMMIT}.tar.gz"
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
TEXT_SUFFIXES = {".md", ".txt", ".json", ".jsonl", ".csv", ".tsv", ".toml", ".yaml", ".yml"}
DISCOVERY_NAMES = {"readme", "license", "copying", "manifest", "schema", "pyproject", "package"}


class ProbeError(RuntimeError):
    pass


def fetch() -> bytes:
    request = Request(ARCHIVE_URL, headers={"User-Agent": "Mercy-Logos-lxx-morph-probe/1.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=90) as response:
                payload = response.read(MAX_ARCHIVE_BYTES + 1)
            if len(payload) > MAX_ARCHIVE_BYTES:
                raise ProbeError("pinned archive exceeds safety size limit")
            return payload
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    raise ProbeError(f"cannot download pinned lxx-morph archive: {last_error}")


def safe_name(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--preview-lines", type=int, default=12)
    args = parser.parse_args()

    payload = fetch()
    archive_sha256 = hashlib.sha256(payload).hexdigest()
    try:
        tf = tarfile.open(fileobj=io.BytesIO(payload), mode="r:gz")
    except tarfile.TarError as exc:
        raise ProbeError(f"pinned archive is not a valid gzip tar: {exc}") from exc

    files = [m for m in tf.getmembers() if m.isfile()]
    if not files:
        raise ProbeError("pinned archive contains no files")
    unsafe = [m.name for m in files if not safe_name(m.name)]
    if unsafe:
        raise ProbeError(f"unsafe archive member paths: {unsafe[:5]}")

    inventory = [{"path": m.name, "size": m.size} for m in files]
    interesting: list[dict] = []
    previews: dict[str, list[str]] = {}
    for member in files:
        p = PurePosixPath(member.name)
        stem = p.stem.lower()
        suffix = p.suffix.lower()
        lower = p.name.lower()
        is_named = any(key in stem or key in lower for key in DISCOVERY_NAMES)
        is_data = suffix in TEXT_SUFFIXES and member.size > 0
        if is_named or is_data:
            interesting.append({"path": member.name, "size": member.size})
        if (is_named or suffix in {".json", ".jsonl", ".tsv", ".csv"}) and 0 < member.size <= 2 * 1024 * 1024:
            source = tf.extractfile(member)
            if source is None:
                continue
            raw = source.read(128 * 1024)
            try:
                text = raw.decode("utf-8-sig")
            except UnicodeDecodeError:
                continue
            previews[member.name] = text.splitlines()[: max(1, args.preview_lines)]

    report = {
        "source": "lxx-morph",
        "commit": COMMIT,
        "archive_url": ARCHIVE_URL,
        "archive_sha256": archive_sha256,
        "archive_size": len(payload),
        "file_count": len(files),
        "inventory": inventory,
        "interesting_files": interesting,
        "previews": previews,
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProbeError as exc:
        raise SystemExit(f"lxx-morph source probe failed: {exc}") from exc
