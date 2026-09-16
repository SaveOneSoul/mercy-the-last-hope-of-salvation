#!/usr/bin/env python3
"""Build the production Swete Septuagint protocanonical OT expansion.

This package complements, rather than replaces, the already accepted
`grc_ot_catholic_swete` package.  Esther, Daniel and the deuterocanonical
books/additions remain in that accepted package.  This script adds the other
37 Catholic OT books from the same immutable First1KGreek/Swete source tree.

Source Greek boundaries are preserved.  No gloss, lemma, morphology or
transliteration is invented.  Runtime API serving remains gated by exact
Douay-Rheims/source numeric chapter/verse identity.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from vendor_old_testament_phase1b import (
    BuildError as SourceBuildError,
    download_pinned,
    fetch_locked_tree,
    parse_tei,
    relative_to_tree,
)

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = (
    ROOT
    / "cloud-backend"
    / "app"
    / "logos_interlinear"
    / "old_testament_septuagint_full"
    / "source-lock.json"
)
DEFAULT_OUTPUT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_ot_swete_protocanonical"
CORPUS_VERSION = "2026.09.16-swete-protocanonical-37"
EXPECTED_BOOK_COUNT = 37


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


def edition_urn(work: str) -> str:
    return f"urn:cts:greekLit:tlg0527.tlg{work}.1st1K-grc1"


def source_path(work: str) -> str:
    return f"data/tlg0527/tlg{work}/tlg0527.tlg{work}.1st1K-grc1.xml"


def canonicalize_verses(row: dict, verses: list[dict]) -> tuple[dict, list[dict]]:
    start = int(row.get("source_chapter_start") or -1)
    end = int(row.get("source_chapter_end") or -1)
    offset = int(row.get("chapter_offset") or 0)
    chapters: dict[str, dict[str, dict]] = {}
    nonnumeric: list[dict] = []

    for verse in verses:
        source_chapter = str(verse.get("source_chapter") or "")
        source_verse = str(verse.get("source_verse") or "")
        if not source_chapter.isdigit() or not source_verse.isdigit():
            nonnumeric.append(verse)
            continue
        source_chapter_n = int(source_chapter)
        if start >= 0 and source_chapter_n < start:
            continue
        if end >= 0 and source_chapter_n > end:
            continue
        canonical_chapter = source_chapter_n + offset
        if canonical_chapter < 1:
            raise BuildError(f"invalid canonical chapter transform for {row['book_id']} source chapter {source_chapter}")
        chapter = chapters.setdefault(str(canonical_chapter), {})
        if source_verse in chapter:
            raise BuildError(f"duplicate canonical locus {row['book_id']} {canonical_chapter}:{source_verse}")
        chapter[source_verse] = {
            "source_reference": verse.get("source_reference"),
            "source_chapter": source_chapter,
            "source_verse": source_verse,
            "surface": verse.get("surface"),
        }

    if not chapters:
        raise BuildError(f"no canonical numeric source verses selected for {row['book_id']}")
    return chapters, nonnumeric


def build(output: Path) -> dict:
    lock = load_json(LOCK_PATH)
    if lock.get("phase") != "Old Testament Septuagint Protocanonical Expansion":
        raise BuildError("unexpected Septuagint source lock")
    if lock.get("production_enabled") is not False:
        raise BuildError("source lock must remain non-production metadata")

    source = lock.get("source") or {}
    books = lock.get("books") or []
    if len(books) != EXPECTED_BOOK_COUNT:
        raise BuildError(f"expected {EXPECTED_BOOK_COUNT} mapped protocanonical books, got {len(books)}")
    if source.get("repository") != "OpenGreekAndLatin/First1KGreek":
        raise BuildError("unexpected Septuagint source repository")
    if source.get("license") != "CC BY-SA 4.0" or source.get("share_alike") is not True:
        raise BuildError("Septuagint ShareAlike source-rights contract changed")

    repo = str(source["repository"])
    commit = str(source["commit"])
    tree_sha = str(source["septuagint_tree_sha"])
    tree_root = str(source["septuagint_path"])
    inventory = fetch_locked_tree(repo, tree_sha)

    target = output.resolve()
    if target == ROOT.resolve():
        raise BuildError("refusing to use repository root as output")
    if target.exists():
        shutil.rmtree(target)
    books_dir = target / "sharealike" / "first1kgreek_swete_cc-by-sa-4.0" / "books"
    books_dir.mkdir(parents=True, exist_ok=True)

    total_chapters = 0
    total_verses = 0
    source_files: dict[str, dict] = {}
    book_stats: list[dict] = []

    for row in books:
        book_id = str(row["book_id"])
        work = str(row["work"])
        path = source_path(work)
        rel = relative_to_tree(path, tree_root)
        expected_blob = inventory.get(rel)
        if not expected_blob:
            raise BuildError(f"locked Swete tree does not contain {path}")

        try:
            payload, sha256 = download_pinned(repo, commit, path, expected_blob)
            witness = {"id": f"{book_id}-SWETE", "edition_urn": edition_urn(work)}
            verses, parsed_counts = parse_tei(payload, witness, str(source["license_target"]))
        except SourceBuildError as exc:
            raise BuildError(str(exc)) from exc

        chapters, nonnumeric = canonicalize_verses(row, verses)
        chapter_count = len(chapters)
        verse_count = sum(len(v) for v in chapters.values())
        total_chapters += chapter_count
        total_verses += verse_count

        source_files.setdefault(
            work,
            {
                "work": work,
                "path": path,
                "git_blob_sha1": expected_blob,
                "sha256": sha256,
                "edition_urn": edition_urn(work),
                "parsed_source_chapter_count": parsed_counts.get("chapter_count"),
                "parsed_source_verse_count": parsed_counts.get("verse_count"),
            },
        )

        book_payload = {
            "schema_version": 1,
            "corpus_id": "grc_ot_swete_protocanonical",
            "book_id": book_id,
            "book": row.get("name"),
            "language": "grc",
            "production_enabled": True,
            "witness_id": f"{book_id}-SWETE",
            "witness_role": "primary-protocanonical-septuagint",
            "source": {
                "repository": repo,
                "commit": commit,
                "work": work,
                "edition_urn": edition_urn(work),
                "path": path,
                "git_blob_sha1": expected_blob,
                "sha256": sha256,
                "license": "CC BY-SA 4.0",
                "share_alike": True,
                "isolation_required": True,
            },
            "mapping": {
                "mode": "canonical-chapter-transform-plus-runtime-exact-verse-identity",
                "source_chapter_start": row.get("source_chapter_start"),
                "source_chapter_end": row.get("source_chapter_end"),
                "chapter_offset": int(row.get("chapter_offset") or 0),
                "automatic_verse_remapping": False,
                "fabricate_verse_boundaries": False,
            },
            "derived_layers": {
                "glosses": False,
                "lemmata": False,
                "morphology": False,
                "transliteration": False,
            },
            "chapter_count": chapter_count,
            "verse_count": verse_count,
            "nonnumeric_source_loci_not_auto_served": nonnumeric,
            "chapters": chapters,
        }
        write_json(books_dir / f"{book_id}.json", book_payload)
        book_stats.append(
            {
                "book_id": book_id,
                "book": row.get("name"),
                "work": work,
                "chapter_count": chapter_count,
                "verse_count": verse_count,
                "nonnumeric_source_locus_count": len(nonnumeric),
            }
        )

    manifest = {
        "schema_version": 1,
        "corpus_id": "grc_ot_swete_protocanonical",
        "corpus_version": CORPUS_VERSION,
        "status": "production-installed",
        "production_enabled": True,
        "language": "grc",
        "scope": "37 protocanonical Catholic Old Testament books complementing the accepted Greek deuterocanonical/Esther/Daniel witness package",
        "book_count": len(book_stats),
        "chapter_count": total_chapters,
        "verse_count": total_verses,
        "supported_canonical_books": [row["book_id"] for row in book_stats],
        "books": book_stats,
        "source": {
            "id": source.get("id"),
            "repository": repo,
            "commit": commit,
            "septuagint_tree_sha": tree_sha,
            "license": "CC BY-SA 4.0",
            "license_target": source.get("license_target"),
            "share_alike": True,
            "isolation_required": True,
            "attribution": source.get("attribution"),
            "locked_files": sorted(source_files.values(), key=lambda x: x["work"]),
        },
        "partition": {
            "path": "sharealike/first1kgreek_swete_cc-by-sa-4.0/books",
            "license": "CC BY-SA 4.0",
            "share_alike": True,
            "isolation_required": True,
        },
        "derived_layers": {
            "glosses": False,
            "lemmata": False,
            "morphology": False,
            "transliteration": False,
        },
        "versification": {
            "canonical_reference_system": "Douay-Rheims Catholic 73-book corpus",
            "source_reference_system": "First1KGreek Swete TEI/CTS",
            "runtime_exact_identity_required": True,
            "automatic_remapping": False,
            "fabricate_verse_boundaries": False,
            "mismatched_chapters_blocked_until_explicit_mapping": True,
            "ezra_nehemiah_source": "Swete Esdras B: source chapters 1-10 => Ezra 1-10; source chapters 11-23 => Nehemiah 1-13",
        },
        "catholic_scope": lock.get("catholic_complement") or {},
        "serving_contract": {
            "english_corpus_unchanged": True,
            "hebrew_aramaic_corpus_unchanged": True,
            "accepted_deuterocanonical_greek_corpus_unchanged": True,
            "no_english_scripture_text_in_package": True,
            "no_fabricated_gloss_or_linguistic_annotation": True,
        },
    }
    write_json(target / "manifest.json", manifest)
    print(
        f"[OT Septuagint] packaged {manifest['book_count']} books / "
        f"{manifest['chapter_count']} chapters / {manifest['verse_count']} numeric source verse records"
    )
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.output)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, SourceBuildError) as exc:
        raise SystemExit(f"OT Septuagint build failed: {exc}") from exc
