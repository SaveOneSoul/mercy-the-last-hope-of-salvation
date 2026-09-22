#!/usr/bin/env python3
"""Generate and validate a deterministic 73-book Logos interlinear coverage audit."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "cloud-backend" / "app"
INTERLINEAR = APP / "logos_interlinear"
CORPORA = APP / "logos_corpus"

DEFAULT_ENGLISH = CORPORA / "eng_douay_rheims_1899"
DEFAULT_SEMITIC = CORPORA / "heb_arc_oshb_wlc"
DEFAULT_GREEK_OT_FULL = CORPORA / "grc_ot_catholic_full"
DEFAULT_GREEK_OT_ACCEPTED = CORPORA / "grc_ot_catholic_swete"
DEFAULT_GREEK_NT = CORPORA / "grc_sblgnt_morphgnt"
DEFAULT_GREEK_NT_FALLBACK = CORPORA / "grc_tagnt_john_fallback"
DEFAULT_LATIN = CORPORA / "lat_vulgate_clementine"
DEFAULT_JSON = INTERLINEAR / "coverage-audit.json"
DEFAULT_MARKDOWN = ROOT / "LOGOS_INTERLINEAR_COVERAGE.md"

AUDIT_VERSION = "2026.09.17"


class AuditError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def chapter_sets(payload: dict[str, Any]) -> dict[str, set[str]]:
    chapters = payload.get("chapters") or {}
    out: dict[str, set[str]] = {}
    for chapter, verses in chapters.items():
        require(isinstance(verses, dict), f"chapter {chapter} is not a verse map")
        out[str(chapter)] = {str(v) for v in verses.keys()}
    return out


def compare_chapter_sets(base: dict[str, set[str]], other: dict[str, set[str]]) -> dict[str, Any]:
    mismatches: list[dict[str, Any]] = []
    for chapter in sorted(set(base) | set(other), key=lambda x: (not x.isdigit(), int(x) if x.isdigit() else x)):
        left = base.get(chapter)
        right = other.get(chapter)
        if left == right:
            continue
        mismatches.append(
            {
                "chapter": chapter,
                "canonical_verse_count": len(left or set()),
                "source_verse_count": len(right or set()),
                "canonical_only": sorted((left or set()) - (right or set())),
                "source_only": sorted((right or set()) - (left or set())),
            }
        )
    return {
        "status": "exact-all-chapters" if not mismatches else "mapping-required",
        "exact": not mismatches,
        "mismatch_chapter_count": len(mismatches),
        "mismatches": mismatches,
    }


def greek_full_sets(payload: dict[str, Any]) -> dict[str, set[str]]:
    mapping = payload.get("mapping") or {}
    offset = int(mapping.get("canonical_chapter_offset") or 0)
    out: dict[str, set[str]] = {}
    for row in payload.get("verses") or []:
        source_chapter = str(row.get("source_chapter") or "")
        source_verse = str(row.get("source_verse") or "")
        if not source_chapter.isdigit() or not source_verse:
            continue
        canonical_chapter = str(int(source_chapter) - offset)
        out.setdefault(canonical_chapter, set()).add(source_verse)
    return out


def status_cell(value: str) -> str:
    return {
        "complete": "Yes",
        "available": "Yes",
        "partial": "Partial",
        "not-applicable": "—",
        "not-installed": "No",
    }.get(value, value)


def short_alignment(row: dict[str, Any]) -> str:
    parts: list[str] = []
    for label, key in (("H/A", "semitic"), ("G", "greek"), ("L", "latin")):
        value = ((row.get(key) or {}).get("versification") or {}).get("status", "n/a")
        if value == "not-applicable":
            continue
        if value == "exact-all-chapters":
            text = "exact"
        elif value == "verified-explicit-map":
            text = "verified map"
        elif value == "component-range-mapping":
            text = "component map"
        elif value == "mixed-exact-and-component-range":
            text = "mixed map"
        elif value == "mapping-required":
            count = ((row.get(key) or {}).get("versification") or {}).get("mismatch_chapter_count", 0)
            text = f"mapping needed ({count} ch)"
        else:
            text = value
        parts.append(f"{label}: {text}")
    return "; ".join(parts) or "n/a"


def build(args: argparse.Namespace) -> dict[str, Any]:
    canon = load(INTERLINEAR / "books.json")
    source_registry = load(INTERLINEAR / "sources-manifest.json")
    books = canon.get("books") or []
    require(len(books) == 73, f"Catholic canon must contain 73 books, found {len(books)}")
    require([int(b.get("order") or 0) for b in books] == list(range(1, 74)), "Catholic canon order must be 1..73")

    sources = {str(s.get("id")): s for s in (source_registry.get("sources") or [])}

    english_manifest = load(args.english_root / "manifest.json")
    semitic_manifest = load(args.semitic_root / "manifest.json")
    semitic_phase = load(args.semitic_root / "phase1a" / "manifest.json")
    greek_ot_full_manifest = load(args.greek_ot_full_root / "manifest.json")
    greek_ot_accepted_manifest = load(args.greek_ot_accepted_root / "manifest.json")
    greek_ot_map = load(args.greek_ot_accepted_root / "versification-map.json")
    greek_nt_manifest = load(args.greek_nt_root / "manifest.json")
    greek_nt_fallback_manifest = load(args.greek_nt_fallback_root / "manifest.json")
    require(greek_nt_fallback_manifest.get("corpus_id") == "grc_tagnt_john_fallback", "unexpected Greek NT fallback corpus")
    require(greek_nt_fallback_manifest.get("production_enabled") is True, "Greek NT fallback is not production-enabled")
    require(int(greek_nt_fallback_manifest.get("verse_count") or 0) == 12, "Greek NT fallback must cover exactly 12 John verses")
    require(int(greek_nt_fallback_manifest.get("token_row_count") or 0) == 198, "Greek NT fallback token-row inventory changed")
    require(greek_nt_fallback_manifest.get("no_fabricated_linguistics") is True, "Greek NT fallback no-fabrication gate missing")
    latin_manifest = load(args.latin_root / "manifest.json")

    require(int(english_manifest.get("book_count") or 0) == 73, "English corpus is not 73 books")
    require(int(latin_manifest.get("book_count") or 0) == 73, "Latin corpus is not 73 books")
    require(int((semitic_manifest.get("phase1a_acceptance") or {}).get("masoretic_book_witness_count") or 0) == 39, "Semitic corpus is not 39 witnesses")
    require(int(greek_ot_full_manifest.get("book_count") or 0) == 39, "Complete Greek OT protocanonical package is not 39 books")
    require(int((greek_nt_manifest.get("phase1_acceptance") or {}).get("book_count") or 0) == 27, "Greek NT package is not 27 books")

    english_index = {str(b.get("id")): b for b in (english_manifest.get("books") or [])}
    latin_index = {str(b.get("id")): b for b in (latin_manifest.get("books") or [])}
    semitic_index = {str(b.get("book_id")): b for b in (semitic_phase.get("books") or [])}
    greek_full_index = {str(b.get("book_id")): b for b in (greek_ot_full_manifest.get("books") or [])}
    accepted_books = set(((greek_ot_accepted_manifest.get("witnesses") or {}).get("supported_canonical_books") or []))
    accepted_identity = {str(x.get("canonical_book")) for x in (greek_ot_map.get("identity_books") or [])}

    require(set(english_index) == {str(b["id"]) for b in books}, "English corpus book inventory does not equal the Catholic canon")
    require(set(latin_index) == {str(b["id"]) for b in books}, "Latin corpus book inventory does not equal the Catholic canon")
    require(len(semitic_index) == 39, "Semitic phase inventory must contain 39 books")
    require(len(greek_full_index) == 39, "Greek OT full inventory must contain 39 books")
    require(len(accepted_books) == 9, "Accepted OT Greek canonical scope must contain 9 books")

    # Validate accepted witness files before reporting their coverage.
    witness_ids = list(((greek_ot_accepted_manifest.get("witnesses") or {}).get("primary_integration") or [])) + list(((greek_ot_accepted_manifest.get("witnesses") or {}).get("parallel") or []))
    witness_root = args.greek_ot_accepted_root / "sharealike" / "first1kgreek_swete_cc-by-sa-4.0" / "witnesses"
    for witness_id in witness_ids:
        require((witness_root / f"{witness_id}.json").exists(), f"missing accepted OT Greek witness {witness_id}")

    english_source = sources.get("drb-challoner") or {}
    semitic_source = sources.get("oshb") or {}
    accepted_greek_source = sources.get("first1kgreek-swete") or {}
    ecc_source = sources.get("open-greek-ecclesiastes") or {}
    latin_source = sources.get("vulgate-clementine") or {}
    for source_id, source in (("drb-challoner", english_source), ("oshb", semitic_source), ("first1kgreek-swete", accepted_greek_source), ("open-greek-ecclesiastes", ecc_source), ("vulgate-clementine", latin_source)):
        require(source and source.get("production_import_allowed") is True, f"source {source_id} is not production-approved")
        require(str(source.get("license") or "").strip(), f"source {source_id} has no license")

    rows: list[dict[str, Any]] = []
    summary = {
        "book_count": 73,
        "english_complete_books": 0,
        "semitic_surface_books": 0,
        "semitic_linguistics_books": 0,
        "greek_surface_books": 0,
        "greek_linguistics_complete_books": 0,
        "greek_linguistics_partial_books": 0,
        "latin_complete_books": 0,
        "books_with_any_versification_gap": 0,
        "books_with_known_gaps": 0,
    }

    full_greek_book_root = args.greek_ot_full_root / "sharealike" / "catholic_lxx_cc-by-sa-4.0" / "books"
    nt_surface_root = args.greek_nt_root / "phase1" / "surface"
    nt_linguistics_root = args.greek_nt_root / "phase1" / "linguistics"
    semitic_surface_root = args.semitic_root / "phase1a" / "surface"
    semitic_linguistics_root = args.semitic_root / "phase1a" / "linguistics"

    for book in books:
        book_id = str(book["id"])
        name = str(book["name"])
        testament = str(book["testament"])
        known_gaps: list[str] = []

        en_meta = english_index[book_id]
        en_path = args.english_root / str(en_meta.get("filename"))
        require(en_path.exists(), f"missing English book file {book_id}")
        en_payload = load(en_path)
        en_sets = chapter_sets(en_payload)
        require(en_sets, f"English book {book_id} has no chapters")
        english = {
            "status": "complete",
            "source": "Douay-Rheims American Edition (1899)",
            "source_id": "drb-challoner",
            "license": str(english_source.get("license")),
            "chapter_count": len(en_sets),
            "verse_count": int(en_meta.get("verse_count") or 0),
        }
        summary["english_complete_books"] += 1

        # Latin is expected for every Catholic book and is compared directly to the DRA numbering.
        lat_meta = latin_index[book_id]
        lat_path = args.latin_root / str(lat_meta.get("filename"))
        require(lat_path.exists(), f"missing Latin book file {book_id}")
        lat_payload = load(lat_path)
        latin_alignment = compare_chapter_sets(en_sets, chapter_sets(lat_payload))
        latin = {
            "status": "complete",
            "source": "Clementine Latin Vulgate",
            "source_id": "vulgate-clementine",
            "license": str(latin_source.get("license")),
            "versification": latin_alignment,
        }
        summary["latin_complete_books"] += 1
        if not latin_alignment["exact"]:
            known_gaps.append(f"Latin/Douay verse identity differs in {latin_alignment['mismatch_chapter_count']} chapter(s).")

        # Hebrew/Aramaic is available only for the 39 Masoretic witnesses.
        if book_id in semitic_index:
            sem_surface_path = semitic_surface_root / f"{book_id}.json"
            sem_ling_path = semitic_linguistics_root / f"{book_id}.json"
            require(sem_surface_path.exists(), f"missing Semitic surface file {book_id}")
            require(sem_ling_path.exists(), f"missing Semitic linguistic file {book_id}")
            sem_surface = load(sem_surface_path)
            sem_alignment = compare_chapter_sets(en_sets, chapter_sets(sem_surface))
            sem_stats = semitic_index[book_id]
            langs: list[str] = []
            if int(sem_stats.get("hebrew_token_count") or 0) > 0:
                langs.append("he")
            if int(sem_stats.get("aramaic_token_count") or 0) > 0:
                langs.append("arc")
            semitic = {
                "status": "complete",
                "languages": langs,
                "lemma_morphology": "available",
                "source": "Open Scriptures Hebrew Bible / Westminster Leningrad Codex",
                "source_id": "oshb",
                "surface_license": str(semitic_manifest.get("source", {}).get("surface_rights") or "Public Domain"),
                "linguistic_license": str(semitic_manifest.get("source", {}).get("linguistic_annotation_license") or semitic_source.get("license")),
                "versification": sem_alignment,
            }
            summary["semitic_surface_books"] += 1
            summary["semitic_linguistics_books"] += 1
            if not sem_alignment["exact"]:
                known_gaps.append(f"OSHB/WLC and Douay verse identity differs in {sem_alignment['mismatch_chapter_count']} chapter(s); runtime blocks those chapters until explicitly mapped.")
        else:
            semitic = {
                "status": "not-applicable",
                "languages": [],
                "lemma_morphology": "not-applicable",
                "source": None,
                "source_id": None,
                "versification": {"status": "not-applicable", "exact": None, "mismatch_chapter_count": 0, "mismatches": []},
            }

        # Greek: NT uses SBLGNT + MorphGNT. OT combines the complete 39-book Greek package
        # with the accepted deuterocanonical/additions package.
        if testament == "NT":
            gr_surface_path = nt_surface_root / f"{book_id}.json"
            gr_ling_path = nt_linguistics_root / f"{book_id}.json"
            require(gr_surface_path.exists(), f"missing Greek NT surface file {book_id}")
            require(gr_ling_path.exists(), f"missing Greek NT linguistic file {book_id}")
            gr_surface = load(gr_surface_path)
            gr_alignment = compare_chapter_sets(en_sets, chapter_sets(gr_surface))
            linguistics_status = "complete"
            greek = {
                "status": "complete",
                "source": "SBL Greek New Testament",
                "source_id": "sblgnt",
                "license": str((greek_nt_manifest.get("sources", {}).get("surface") or {}).get("license")),
                "lemma_morphology": linguistics_status,
                "linguistic_source": ("MorphGNT SBLGNT + STEPBible TAGNT supplemental" if book_id == "JHN" else "MorphGNT SBLGNT"),
                "linguistic_license": (
                    "CC BY-SA 3.0 (MorphGNT) + CC BY 4.0 (TAGNT supplemental)"
                    if book_id == "JHN"
                    else str((greek_nt_manifest.get("sources", {}).get("linguistics") or {}).get("license"))
                ),
                "versification": gr_alignment,
            }
            if book_id == "JHN":
                require(
                    greek_nt_fallback_manifest.get("references") == ["7:53","8:1","8:2","8:3","8:4","8:5","8:6","8:7","8:8","8:9","8:10","8:11"],
                    "TAGNT John fallback reference inventory changed",
                )
            summary["greek_linguistics_complete_books"] += 1
            if not gr_alignment["exact"]:
                known_gaps.append(f"SBLGNT and Douay verse identity differs in {gr_alignment['mismatch_chapter_count']} chapter(s).")
        else:
            # Runtime gives the accepted Catholic-additions package precedence where it applies,
            # and falls back to the complete protocanonical package outside that accepted scope.
            if book_id in accepted_identity:
                gr_alignment = {"status": "exact-all-chapters", "exact": True, "mismatch_chapter_count": 0, "mismatches": []}
                gr_source = "Swete Septuagint witness"
                gr_source_id = "first1kgreek-swete"
                gr_license = str(accepted_greek_source.get("license"))
            elif book_id == "BAR":
                gr_alignment = {"status": "verified-explicit-map", "exact": True, "mismatch_chapter_count": 0, "mismatches": []}
                gr_source = "Swete Baruch + Epistle of Jeremiah"
                gr_source_id = "first1kgreek-swete"
                gr_license = str(accepted_greek_source.get("license"))
            elif book_id == "EST":
                gr_alignment = {"status": "component-range-mapping", "exact": False, "mismatch_chapter_count": 7, "mismatches": []}
                gr_source = "Swete Greek Esther + complete protocanonical Greek fallback"
                gr_source_id = "first1kgreek-swete"
                gr_license = str(accepted_greek_source.get("license"))
                known_gaps.append("Greek Esther additions use component-range mapping; whole-chapter runtime assembly across base text and additions is composite rather than one-to-one.")
            elif book_id == "DAN":
                gr_alignment = {"status": "mixed-exact-and-component-range", "exact": False, "mismatch_chapter_count": 1, "mismatches": []}
                gr_source = "Theodotion/Old Greek additions + complete protocanonical Greek fallback"
                gr_source_id = "first1kgreek-swete"
                gr_license = str(accepted_greek_source.get("license"))
                known_gaps.append("Daniel 14 uses a 36-source-verse to 42-Douay component-range mapping; full-chapter Greek assembly is composite.")
            else:
                require(book_id in greek_full_index, f"OT book {book_id} has no Greek surface source")
                gr_path = full_greek_book_root / f"{book_id}.json"
                require(gr_path.exists(), f"missing complete Greek OT book file {book_id}")
                gr_payload = load(gr_path)
                gr_alignment = compare_chapter_sets(en_sets, greek_full_sets(gr_payload))
                if book_id == "ECC":
                    gr_source = "Greek Wikisource Ecclesiastes via Open Greek Corpus"
                    gr_source_id = "open-greek-ecclesiastes"
                    gr_license = str(ecc_source.get("license"))
                else:
                    gr_source = "First1KGreek / Swete Septuagint"
                    gr_source_id = "first1kgreek-swete"
                    gr_license = str(accepted_greek_source.get("license"))
                empty_count = int(greek_full_index[book_id].get("empty_source_surface_count") or 0)
                if empty_count:
                    known_gaps.append(f"Pinned Greek witness preserves {empty_count} explicitly empty source verse division(s); no Greek text is fabricated.")
                if not gr_alignment["exact"]:
                    known_gaps.append(f"Greek/Douay verse identity differs in {gr_alignment['mismatch_chapter_count']} chapter(s); those chapters require explicit mapping.")
            greek = {
                "status": "complete",
                "source": gr_source,
                "source_id": gr_source_id,
                "license": gr_license,
                "lemma_morphology": "not-installed",
                "linguistic_source": None,
                "linguistic_license": None,
                "versification": gr_alignment,
            }

        summary["greek_surface_books"] += 1
        if testament == "OT":
            # This is a deliberate integrity boundary, not fabricated missing data.
            pass

        if known_gaps:
            summary["books_with_known_gaps"] += 1
        if any(
            ((lane.get("versification") or {}).get("exact") is False)
            for lane in (semitic, greek, latin)
            if lane.get("status") != "not-applicable"
        ):
            summary["books_with_any_versification_gap"] += 1

        rows.append(
            {
                "order": int(book["order"]),
                "id": book_id,
                "book": name,
                "testament": testament,
                "profile": book.get("profile"),
                "english": english,
                "semitic": semitic,
                "greek": greek,
                "latin": latin,
                "known_gaps": known_gaps,
            }
        )

    require(summary["english_complete_books"] == 73, "English coverage is not complete for 73 books")
    require(summary["latin_complete_books"] == 73, "Latin coverage is not complete for 73 books")
    require(summary["semitic_surface_books"] == 39, "Semitic surface coverage is not exactly 39 books")
    require(summary["semitic_linguistics_books"] == 39, "Semitic linguistic coverage is not exactly 39 books")
    require(summary["greek_surface_books"] == 73, "Greek surface witness coverage is not represented for all 73 books")
    require(summary["greek_linguistics_complete_books"] + summary["greek_linguistics_partial_books"] == 27, "Greek NT linguistic coverage is not represented for all 27 NT books")

    return {
        "schema_version": 1,
        "audit_version": AUDIT_VERSION,
        "canon": "Catholic 73-book canon",
        "policy": {
            "english_primary": "Douay-Rheims American Edition (1899)",
            "original_language_claim": "Source-language witnesses are reported according to their actual textual editions; they are not relabeled as Catholic editions.",
            "latin_role": "Historic Catholic ecclesial translation, not an original biblical language.",
            "no_fabricated_alignment": True,
            "no_fabricated_linguistics": True,
        },
        "corpus_versions": {
            "english": english_manifest.get("corpus_version"),
            "semitic": semitic_manifest.get("corpus_version"),
            "greek_ot_full": greek_ot_full_manifest.get("corpus_version"),
            "greek_ot_accepted": greek_ot_accepted_manifest.get("corpus_version"),
            "greek_nt": greek_nt_manifest.get("corpus_version"),
            "greek_nt_fallback": greek_nt_fallback_manifest.get("corpus_version"),
            "latin": latin_manifest.get("corpus_version"),
        },
        "summary": summary,
        "books": rows,
    }


def render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Logos 73-Book Interlinear Coverage Audit",
        "",
        "This file is generated deterministically by `tools/audit_logos_73_book_interlinear.py`. Do not hand-edit the matrix.",
        "",
        "## Coverage summary",
        "",
        f"- Catholic canon: **{summary['book_count']} books**",
        f"- Douay-Rheims English: **{summary['english_complete_books']}/73 books**",
        f"- Hebrew/Aramaic OSHB/WLC surface + lemma/morphology: **{summary['semitic_surface_books']} books**",
        f"- Greek surface witnesses represented: **{summary['greek_surface_books']}/73 books**",
        f"- Greek lemma/POS/morphology: **{summary['greek_linguistics_complete_books']}/27 NT books complete** (John 7:53–8:11 uses the separately pinned TAGNT supplemental witness); **OT Greek linguistic layer is not installed**",
        f"- Clementine Latin Vulgate: **{summary['latin_complete_books']}/73 books**",
        f"- Books with at least one explicit versification boundary/gap: **{summary['books_with_any_versification_gap']}**",
        f"- Books with recorded known gaps/limitations: **{summary['books_with_known_gaps']}**",
        "",
        "`Exact` means the source chapter/verse identifiers match the Douay-Rheims canonical reference system for the audited scope. `Verified map` and `component map` mean an explicit source-to-Catholic mapping is recorded instead of forcing a false one-to-one correspondence.",
        "",
        "## Per-book matrix",
        "",
        "| # | Book | T | Douay-Rheims | Hebrew/Aramaic | Greek surface | Greek lemma/morph | Clementine Latin | Versification | Source / license | Known gaps |",
        "|---:|---|:--:|---|---|---|---|---|---|---|---|",
    ]
    for row in report["books"]:
        sem = row["semitic"]
        gr = row["greek"]
        lat = row["latin"]
        sem_text = "—" if sem["status"] == "not-applicable" else "/".join(sem.get("languages") or []) + " + lemma/morph"
        greek_ling = status_cell(gr.get("lemma_morphology", "not-installed"))
        source_parts = [
            f"EN: {row['english']['source']} ({row['english']['license']})",
            f"G: {gr['source']} ({gr['license']})",
            f"L: {lat['source']} ({lat['license']})",
        ]
        if sem["status"] != "not-applicable":
            source_parts.append(f"H/A: {sem['source']} ({sem.get('linguistic_license')})")
        gaps = "; ".join(row.get("known_gaps") or []) or "—"
        cells = [
            str(row["order"]),
            row["book"],
            row["testament"],
            "Yes",
            sem_text,
            "Yes",
            greek_ling,
            "Yes",
            short_alignment(row),
            "<br>".join(source_parts),
            gaps.replace("|", "\\|"),
        ]
        lines.append("| " + " | ".join(cells) + " |")
    lines.extend(
        [
            "",
            "## Integrity interpretation",
            "",
            "- The **Douay-Rheims 1899** corpus is the primary Catholic 73-book reading/reference system.",
            "- **Hebrew/Aramaic** comes from OSHB/WLC where a Masoretic witness exists; source lemma and morphology are preserved.",
            "- **Old Testament Greek** comes from pinned Septuagint witnesses. Greek additions and deuterocanonical material are treated as normal Catholic canonical material, while unsafe verse correspondences remain component-level or mapping-required.",
            "- **New Testament Greek** uses SBLGNT surface text and MorphGNT lemma/POS/morphology; John 7:53–8:11 is completed by a separately pinned STEPBible TAGNT CC BY 4.0 supplemental linguistic witness without claiming cross-edition token identity.",
            "- **Clementine Latin** is available across all 73 books as a historic Catholic ecclesial witness, not as an original-language source.",
            "- The audit fails if a required corpus/book file disappears, a canonical inventory shrinks, or an expected production source/license gate is lost. Known textual/versification differences are reported rather than fabricated away.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--english-root", type=Path, default=DEFAULT_ENGLISH)
    parser.add_argument("--semitic-root", type=Path, default=DEFAULT_SEMITIC)
    parser.add_argument("--greek-ot-full-root", type=Path, default=DEFAULT_GREEK_OT_FULL)
    parser.add_argument("--greek-ot-accepted-root", type=Path, default=DEFAULT_GREEK_OT_ACCEPTED)
    parser.add_argument("--greek-nt-root", type=Path, default=DEFAULT_GREEK_NT)
    parser.add_argument("--greek-nt-fallback-root", type=Path, default=DEFAULT_GREEK_NT_FALLBACK)
    parser.add_argument("--latin-root", type=Path, default=DEFAULT_LATIN)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()

    for key in ("english_root", "semitic_root", "greek_ot_full_root", "greek_ot_accepted_root", "greek_nt_root", "greek_nt_fallback_root", "latin_root"):
        setattr(args, key, getattr(args, key).resolve())

    report = build(args)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render_markdown(report), encoding="utf-8")

    summary = report["summary"]
    print(
        "Logos 73-book interlinear audit passed: "
        f"EN {summary['english_complete_books']}/73; "
        f"H/A {summary['semitic_surface_books']}; "
        f"Greek surface {summary['greek_surface_books']}/73; "
        f"Greek linguistics {summary['greek_linguistics_complete_books']} complete + "
        f"{summary['greek_linguistics_partial_books']} partial; "
        f"Latin {summary['latin_complete_books']}/73; "
        f"known-gap books {summary['books_with_known_gaps']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        raise SystemExit(f"Logos 73-book interlinear audit failed: {exc}") from exc
