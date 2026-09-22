#!/usr/bin/env python3
"""Build the 46-book Catholic Greek OT Rahlfs/lxx-morph validation corpus.

The installed Swete/Open Greek surface corpora are NOT modified. This package
preserves lxx-morph's Rahlfs 1935 word records as a distinct linguistic witness.
No cross-edition token attachment or canonical versification remapping occurs
in this phase.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import shutil
import tarfile
import time
from collections import Counter
from pathlib import Path, PurePosixPath
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "build" / "logos-greek-ot-linguistics-phase2"
COMMIT = "c91f6b1e8fb3ba37df701e6ae31f675ace71a2b2"
ARCHIVE_URL = f"https://git.sr.ht/~sethkush/lxx-morph/archive/{COMMIT}.tar.gz"
ARCHIVE_SHA256 = "b3c4861f47152ea8fab7d3ed78d807a9a0c2b35d07f2cb64fa9deefd6ac960a9"
MAX_ARCHIVE_BYTES = 256 * 1024 * 1024
CORPUS_ID = "grc_ot_rahlfs_lxx_morph"
CORPUS_VERSION = "2026.09.22-c91f6b1-validation"
REQUIRED_WORD_FIELDS = {"surface", "lemma", "parsing", "pos", "confidence", "source", "reasoning"}
REF_RE = re.compile(r"^(.+?)\s+(\d+):(.+)$")

BOOK_COMPONENTS = {
    "GEN": [("genesis.json", None)],
    "EXO": [("exodus.json", None)],
    "LEV": [("leviticus.json", None)],
    "NUM": [("numbers.json", None)],
    "DEU": [("deuteronomy.json", None)],
    "JOS": [("joshua.json", None)],
    "JDG": [("judges.json", None)],
    "RUT": [("ruth.json", None)],
    "1SA": [("1-samuel.json", None)],
    "2SA": [("2-samuel.json", None)],
    "1KI": [("1-kings.json", None)],
    "2KI": [("2-kings.json", None)],
    "1CH": [("1-chronicles.json", None)],
    "2CH": [("2-chronicles.json", None)],
    "EZR": [("2-esdras.json", (1, 10))],
    "NEH": [("2-esdras.json", (11, 23))],
    "TOB": [("tobit.json", None)],
    "JDT": [("judith.json", None)],
    "EST": [("esther-greek.json", None)],
    "1MA": [("1-maccabees.json", None)],
    "2MA": [("2-maccabees.json", None)],
    "JOB": [("job-lxx.json", None)],
    "PSA": [("psalms-lxx.json", None)],
    "PRO": [("proverbs.json", None)],
    "ECC": [("ecclesiastes.json", None)],
    "SNG": [("song-of-solomon.json", None)],
    "WIS": [("wisdom.json", None)],
    "SIR": [("sirach.json", None)],
    "ISA": [("isaiah.json", None)],
    "JER": [("jeremiah-lxx.json", None)],
    "LAM": [("lamentations.json", None)],
    "BAR": [("baruch.json", None), ("letter-of-jeremiah.json", None)],
    "EZK": [("ezekiel.json", None)],
    "DAN": [
        ("daniel-theodotion.json", None),
        ("susanna-theodotion.json", None),
        ("bel-and-the-dragon-theodotion.json", None),
    ],
    "HOS": [("hosea.json", None)],
    "JOL": [("joel.json", None)],
    "AMO": [("amos.json", None)],
    "OBA": [("obadiah.json", None)],
    "JON": [("jonah.json", None)],
    "MIC": [("micah.json", None)],
    "NAM": [("nahum.json", None)],
    "HAB": [("habakkuk.json", None)],
    "ZEP": [("zephaniah.json", None)],
    "HAG": [("haggai.json", None)],
    "ZEC": [("zechariah.json", None)],
    "MAL": [("malachi.json", None)],
}


class BuildError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def request_archive() -> bytes:
    request = Request(ARCHIVE_URL, headers={"User-Agent": "Mercy-Logos-Greek-OT-Linguistics/1.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=90) as response:
                payload = response.read(MAX_ARCHIVE_BYTES + 1)
            if len(payload) > MAX_ARCHIVE_BYTES:
                raise BuildError("pinned lxx-morph archive exceeds size safety limit")
            actual = hashlib.sha256(payload).hexdigest()
            if actual != ARCHIVE_SHA256:
                raise BuildError(f"lxx-morph archive SHA-256 mismatch: expected {ARCHIVE_SHA256}, got {actual}")
            return payload
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    raise BuildError(f"cannot download pinned lxx-morph archive: {last_error}")


def safe_member(name: str) -> bool:
    path = PurePosixPath(name)
    return bool(name) and not path.is_absolute() and ".." not in path.parts


def members_by_suffix(tf: tarfile.TarFile) -> dict[str, tarfile.TarInfo]:
    output: dict[str, tarfile.TarInfo] = {}
    for member in tf.getmembers():
        if not member.isfile():
            continue
        if not safe_member(member.name):
            raise BuildError(f"unsafe archive path: {member.name}")
        for suffix in ("LICENSE-DATA", "README.md"):
            if member.name.endswith("/" + suffix):
                output[suffix] = member
        if "/db/seeds/lxx_morph/" in member.name:
            rel = member.name.split("/db/seeds/lxx_morph/", 1)[1]
            if "/" not in rel and rel.endswith(".json"):
                output["data:" + rel] = member
    return output


def read_member(tf: tarfile.TarFile, member: tarfile.TarInfo) -> bytes:
    source = tf.extractfile(member)
    if source is None:
        raise BuildError(f"cannot read archive member {member.name}")
    return source.read()


def parse_component(payload: bytes, filename: str) -> list[dict]:
    try:
        rows = json.loads(payload.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise BuildError(f"{filename}: invalid UTF-8 JSON: {exc}") from exc
    if not isinstance(rows, list) or not rows:
        raise BuildError(f"{filename}: final morphology file must be a non-empty JSON array")

    seen: set[str] = set()
    output: list[dict] = []
    for row_index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            raise BuildError(f"{filename}: row {row_index} is not an object")
        ref = str(row.get("ref") or "").strip()
        if not ref or ref in seen:
            raise BuildError(f"{filename}: missing/duplicate source ref {ref!r}")
        seen.add(ref)
        words = row.get("words")
        if not isinstance(words, list) or not words:
            raise BuildError(f"{filename} {ref}: words must be a non-empty list")

        tokens: list[dict] = []
        for position, word in enumerate(words, start=1):
            if not isinstance(word, dict):
                raise BuildError(f"{filename} {ref} token {position}: word row is not an object")
            missing = REQUIRED_WORD_FIELDS - set(word)
            if missing:
                raise BuildError(f"{filename} {ref} token {position}: missing fields {sorted(missing)}")
            surface = str(word.get("surface") or "").strip()
            lemma = str(word.get("lemma") or "").strip()
            pos = str(word.get("pos") or "").strip()
            source = str(word.get("source") or "").strip()
            reasoning = str(word.get("reasoning") or "").strip()
            if not surface or not lemma or not pos or not source or not reasoning:
                raise BuildError(f"{filename} {ref} token {position}: required linguistic value is empty")
            tokens.append(
                {
                    "position": position,
                    "surface": surface,
                    "lemma": lemma,
                    "morphology": str(word.get("parsing") or ""),
                    "part_of_speech": pos,
                    "confidence": word.get("confidence"),
                    "provenance_source": source,
                    "reasoning": reasoning,
                }
            )
        output.append({"source_ref": ref, "tokens": tokens})
    return output


def source_chapter(ref: str) -> int | None:
    match = REF_RE.fullmatch(ref)
    if not match:
        return None
    return int(match.group(2))


def filter_component(rows: list[dict], chapter_range: tuple[int, int] | None, filename: str) -> list[dict]:
    if chapter_range is None:
        return rows
    start, end = chapter_range
    selected = [row for row in rows if (source_chapter(row["source_ref"]) or -1) in range(start, end + 1)]
    if not selected:
        raise BuildError(f"{filename}: chapter filter {start}-{end} produced no verses")
    return selected


def write_json(path: Path, payload: dict, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")


def build(output: Path) -> dict:
    books = load_json(ROOT / "cloud-backend" / "app" / "logos_interlinear" / "books.json").get("books") or []
    ot = [row for row in books if row.get("testament") == "OT"]
    expected_ids = [str(row["id"]) for row in ot]
    if len(expected_ids) != 46 or set(BOOK_COMPONENTS) != set(expected_ids):
        raise BuildError("Catholic OT component map must exactly cover all 46 OT book ids")

    archive = request_archive()
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as tf:
        members = members_by_suffix(tf)
        license_member = members.get("LICENSE-DATA")
        readme_member = members.get("README.md")
        if license_member is None or readme_member is None:
            raise BuildError("pinned archive lacks README.md or LICENSE-DATA")
        license_bytes = read_member(tf, license_member)
        readme_bytes = read_member(tf, readme_member)
        if b"Creative Commons Attribution 4.0 International License (CC BY 4.0)" not in license_bytes:
            raise BuildError("lxx-morph data license declaration changed")
        if b"db/seeds/lxx_morph/" not in license_bytes:
            raise BuildError("lxx-morph data license scope changed")
        if b"Word-level morphological data for the Rahlfs Septuagint (1935)" not in readme_bytes:
            raise BuildError("lxx-morph README edition identity changed")

        cache: dict[str, tuple[list[dict], str]] = {}
        for filename in sorted({name for bindings in BOOK_COMPONENTS.values() for name, _ in bindings}):
            member = members.get("data:" + filename)
            if member is None:
                raise BuildError(f"pinned archive missing required final morphology file {filename}")
            payload = read_member(tf, member)
            cache[filename] = (parse_component(payload, filename), hashlib.sha256(payload).hexdigest())

    if output.exists():
        shutil.rmtree(output)
    book_dir = output / "books"
    book_dir.mkdir(parents=True, exist_ok=True)

    total_verses = 0
    total_tokens = 0
    confidence_counts: Counter[str] = Counter()
    provenance_counts: Counter[str] = Counter()
    manifest_books: list[dict] = []
    file_inventory: dict[str, dict] = {}

    by_id = {str(row["id"]): row for row in ot}
    for book_id in expected_ids:
        book = by_id[book_id]
        bindings = BOOK_COMPONENTS[book_id]
        verses: list[dict] = []
        components: list[dict] = []
        seen_refs: set[tuple[str, str]] = set()

        for filename, chapter_range in bindings:
            rows, sha256 = cache[filename]
            selected = filter_component(rows, chapter_range, filename)
            component_id = filename[:-5]
            for row in selected:
                key = (component_id, row["source_ref"])
                if key in seen_refs:
                    raise BuildError(f"{book_id}: duplicate component/source ref {key}")
                seen_refs.add(key)
                tokens = row["tokens"]
                for token in tokens:
                    confidence_counts[str(token.get("confidence"))] += 1
                    provenance_counts[str(token.get("provenance_source"))] += 1
                verses.append(
                    {
                        "component": component_id,
                        "source_ref": row["source_ref"],
                        "tokens": tokens,
                    }
                )
                total_tokens += len(tokens)
            total_verses += len(selected)
            component_meta = {
                "component": component_id,
                "source_file": filename,
                "source_file_sha256": sha256,
                "verse_count": len(selected),
                "chapter_filter": list(chapter_range) if chapter_range is not None else None,
            }
            components.append(component_meta)
            file_inventory[filename] = {
                "path": f"db/seeds/lxx_morph/{filename}",
                "sha256": sha256,
                "full_file_verse_count": len(rows),
            }

        payload = {
            "schema_version": 1,
            "corpus_id": CORPUS_ID,
            "corpus_version": CORPUS_VERSION,
            "status": "validation-only",
            "production_enabled": False,
            "book_id": book_id,
            "book": book["name"],
            "language": "grc",
            "text_edition": "Rahlfs Septuagint (1935)",
            "linguistic_source": "lxx-morph-rahlfs",
            "license": "CC BY 4.0",
            "source_reference_system": "lxx-morph-native-rahlfs-references",
            "cross_edition_policy": {
                "installed_surface_witness": "Swete/First1KGreek or explicit installed fallback",
                "relationship": "separate-witness",
                "automatic_attachment_to_installed_surface": False,
                "canonical_versification_remapping": False,
            },
            "components": components,
            "verse_count": len(verses),
            "token_count": sum(len(row["tokens"]) for row in verses),
            "verses": verses,
        }
        write_json(book_dir / f"{book_id}.json", payload)
        manifest_books.append(
            {
                "order": book["order"],
                "book_id": book_id,
                "book": book["name"],
                "component_count": len(components),
                "verse_count": payload["verse_count"],
                "token_count": payload["token_count"],
                "components": components,
            }
        )

    manifest = {
        "schema_version": 1,
        "corpus_id": CORPUS_ID,
        "corpus_version": CORPUS_VERSION,
        "status": "validation-only",
        "production_enabled": False,
        "language": "grc",
        "scope": "All 46 Catholic Old Testament books as a separate Rahlfs 1935 word-level linguistic witness.",
        "book_count": 46,
        "verse_record_count": total_verses,
        "token_count": total_tokens,
        "source": {
            "source_id": "lxx-morph-rahlfs",
            "repository": "https://git.sr.ht/~sethkush/lxx-morph",
            "commit": COMMIT,
            "archive_url": ARCHIVE_URL,
            "archive_sha256": ARCHIVE_SHA256,
            "license": "CC BY 4.0",
            "license_path": "LICENSE-DATA",
            "data_path": "db/seeds/lxx_morph/",
            "text_edition": "Rahlfs Septuagint (1935)",
            "attribution": "lxx-morph morphology by Seth Kushniryk; Rahlfs 1935 source text is public domain.",
        },
        "source_file_inventory": file_inventory,
        "books": manifest_books,
        "field_provenance": {
            "surface": "lxx-morph final work JSON / Rahlfs 1935",
            "lemma": "lxx-morph",
            "part_of_speech": "lxx-morph",
            "morphology": "lxx-morph parsing",
            "confidence": "lxx-morph",
            "provenance_source": "lxx-morph source field",
            "reasoning": "lxx-morph reasoning field",
        },
        "confidence_counts": dict(sorted(confidence_counts.items())),
        "provenance_source_counts": dict(sorted(provenance_counts.items())),
        "runtime_contract": {
            "source_native_references_preserved": True,
            "source_token_order_preserved": True,
            "automatic_attachment_to_swete": False,
            "automatic_canonical_remapping": False,
            "cross_edition_relabeling_forbidden": True,
            "no_fabricated_linguistics": True,
            "no_glosses_added": True,
            "no_transliteration_added": True,
        },
        "quality_note": "Open linguistic data with per-token provenance/confidence; preserve those fields and verify against an authoritative edition for scholarly citation.",
    }
    write_json(output / "manifest.json", manifest, pretty=True)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    manifest = build(args.output.resolve())
    print(
        "Greek OT linguistic validation corpus built: "
        f"{manifest['book_count']} Catholic OT books, "
        f"{manifest['verse_record_count']} source verse records, "
        f"{manifest['token_count']} word tokens; Rahlfs witness kept separate from Swete"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        raise SystemExit(f"Greek OT linguistic build failed: {exc}") from exc
