#!/usr/bin/env python3
"""Build the production Swete Septuagint protocanonical OT expansion.

This package complements, rather than replaces, the already accepted
`grc_ot_catholic_swete` package. Esther, Daniel and the deuterocanonical
books/additions remain in that accepted package. This script adds the other
37 Catholic OT books from the same immutable First1KGreek/Swete source tree.

Source Greek boundaries are preserved. Empty TEI verse divs are retained as
explicit source gaps rather than guessed from neighboring text. No gloss,
lemma, morphology or transliteration is invented. Runtime API serving remains
gated by exact Douay-Rheims/source numeric chapter/verse identity.
"""

from __future__ import annotations

import argparse
import json
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

from vendor_old_testament_phase1b import (
    BuildError as SourceBuildError,
    download_pinned,
    fetch_locked_tree,
    local_name,
    relative_to_tree,
    surface_text,
    verify_tei_license,
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


def parse_tei_tolerant(payload: bytes, witness_id: str, selected_edition: str, license_target: str) -> tuple[list[dict], dict, list[dict]]:
    """Parse Swete TEI without inventing text for malformed/empty verse divs.

    The accepted Phase 1B parser deliberately hard-fails empty surfaces. For a
    full 37-book production inventory, an upstream TEI encoding defect such as
    Deuteronomy 25:19 must not make unrelated books unavailable. We therefore
    preserve the empty locus as a source gap and omit it from auto-served verse
    surfaces. The runtime exact-identity gate consequently blocks that chapter.
    """
    try:
        root = ET.fromstring(payload)
    except ET.ParseError as exc:
        raise BuildError(f"{witness_id}: invalid TEI XML: {exc}") from exc
    verify_tei_license(root, witness_id, license_target)
    edition_nodes = [
        node
        for node in root.iter()
        if local_name(node.tag) == "div"
        and node.attrib.get("type") == "edition"
        and node.attrib.get("n") == selected_edition
    ]
    if len(edition_nodes) != 1:
        raise BuildError(f"{witness_id}: expected exactly one selected TEI edition div")

    verses: list[dict] = []
    gaps: list[dict] = []
    seen: set[tuple[str | None, str]] = set()
    chapters_seen: set[str] = set()

    def walk(node: ET.Element, chapter: str | None = None) -> None:
        if local_name(node.tag) == "div" and node.attrib.get("subtype") == "chapter":
            chapter = str(node.attrib.get("n") or "")
            if not chapter:
                raise BuildError(f"{witness_id}: chapter without source n")
            chapters_seen.add(chapter)
        if local_name(node.tag) == "div" and node.attrib.get("subtype") == "verse":
            verse = str(node.attrib.get("n") or "")
            if not verse:
                raise BuildError(f"{witness_id}: verse without source n")
            key = (chapter, verse)
            if key in seen:
                raise BuildError(f"{witness_id}: duplicate source locus {chapter}:{verse}")
            seen.add(key)
            source_ref = f"{chapter}:{verse}" if chapter is not None else verse
            text = surface_text(node)
            if not text:
                gaps.append(
                    {
                        "source_chapter": chapter,
                        "source_verse": verse,
                        "source_reference": source_ref,
                        "reason": "empty_source_tei_verse_div",
                        "fabricated_surface": False,
                    }
                )
                return
            verses.append(
                {
                    "source_chapter": chapter,
                    "source_verse": verse,
                    "source_reference": source_ref,
                    "surface": text,
                }
            )
            return
        for child in list(node):
            walk(child, chapter)

    walk(edition_nodes[0])
    if not verses:
        raise BuildError(f"{witness_id}: no nonempty TEI verse surfaces parsed")
    return verses, {"verse_div_count": len(seen), "surface_verse_count": len(verses), "chapter_count": len(chapters_seen)}, gaps


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


def gap_in_book_range(row: dict, gap: dict) -> bool:
    chapter = str(gap.get("source_chapter") or "")
    if not chapter.isdigit():
        return True
    chapter_n = int(chapter)
    start = int(row.get("source_chapter_start") or -1)
    end = int(row.get("source_chapter_end") or -1)
    if start >= 0 and chapter_n < start:
        return False
    if end >= 0 and chapter_n > end:
        return False
    return True


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
    total_source_gaps = 0
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
            verses, parsed_counts, source_gaps = parse_tei_tolerant(
                payload,
                f"{book_id}-SWETE",
                edition_urn(work),
                str(source["license_target"]),
            )
        except SourceBuildError as exc:
            raise BuildError(str(exc)) from exc

        chapters, nonnumeric = canonicalize_verses(row, verses)
        relevant_gaps = [gap for gap in source_gaps if gap_in_book_range(row, gap)]
        chapter_count = len(chapters)
        verse_count = sum(len(v) for v in chapters.values())
        total_chapters += chapter_count
        total_verses += verse_count
        total_source_gaps += len(relevant_gaps)

        source_files.setdefault(
            work,
            {
                "work": work,
                "path": path,
                "git_blob_sha1": expected_blob,
                "sha256": sha256,
                "edition_urn": edition_urn(work),
                "parsed_source_chapter_count": parsed_counts.get("chapter_count"),
                "parsed_source_verse_div_count": parsed_counts.get("verse_div_count"),
                "parsed_surface_verse_count": parsed_counts.get("surface_verse_count"),
                "empty_source_locus_count": len(source_gaps),
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
            "empty_source_loci_not_auto_served": relevant_gaps,
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
                "empty_source_locus_count": len(relevant_gaps),
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
        "empty_source_locus_count": total_source_gaps,
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
            "empty_source_loci_are_not_filled_from_neighboring_text": True,
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
            "no_fabricated_source_surface_for_empty_tei_loci": True,
        },
    }
    write_json(target / "manifest.json", manifest)
    print(
        f"[OT Septuagint] packaged {manifest['book_count']} books / "
        f"{manifest['chapter_count']} chapters / {manifest['verse_count']} nonempty numeric source verse surfaces; "
        f"{manifest['empty_source_locus_count']} explicit empty source loci retained as gaps"
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
