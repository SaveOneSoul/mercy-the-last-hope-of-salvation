#!/usr/bin/env python3
"""Validate the Logos Catholic versification mapping registry and verified map files."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
APP = ROOT / "cloud-backend" / "app"
INTERLINEAR = APP / "logos_interlinear"
VERS = INTERLINEAR / "versification"
CORPORA = APP / "logos_corpus"
INDEX = VERS / "index.json"
BOOKS = INTERLINEAR / "books.json"
AUDIT = INTERLINEAR / "coverage-audit.json"

ALLOWED_LANES = {"semitic", "greek", "latin"}
ALLOWED_STATUS = {"draft", "verified"}
ALLOWED_RELATIONSHIPS = {
    "identity",
    "renumber",
    "offset",
    "split",
    "merge",
    "range",
    "component-range",
    "source-only",
    "canonical-only",
}


class ValidationError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def safe_mapping_path(value: str) -> Path:
    relative = Path(value)
    require(not relative.is_absolute(), f"mapping path must be relative: {value}")
    require(".." not in relative.parts, f"mapping path may not traverse parents: {value}")
    require(relative.parts and relative.parts[0] == "maps", f"mapping file must live under maps/: {value}")
    require(relative.suffix.lower() == ".json", f"mapping file must be JSON: {value}")
    resolved = (VERS / relative).resolve()
    require(VERS.resolve() in resolved.parents, f"mapping path escapes registry root: {value}")
    return resolved


def ref_tuple(value: dict[str, Any], where: str) -> tuple[str, str]:
    chapter = str(value.get("chapter") or "").strip()
    verse = str(value.get("verse") or "").strip()
    require(chapter.isdigit() and int(chapter) > 0, f"{where}: invalid chapter {chapter!r}")
    require(bool(verse), f"{where}: missing verse")
    return chapter, verse


def canonical_inventory() -> tuple[dict[str, dict[str, Any]], dict[str, set[tuple[str, str]]]]:
    books_payload = load(BOOKS)
    books = books_payload.get("books") or []
    require(len(books) == 73, "Catholic canonical registry must contain 73 books")
    book_index = {str(row.get("id")): row for row in books}

    manifest = load(CORPORA / "eng_douay_rheims_1899" / "manifest.json")
    by_id = {str(row.get("id")): row for row in manifest.get("books") or []}
    require(set(by_id) == set(book_index), "Douay-Rheims corpus inventory does not equal Catholic canon")
    refs: dict[str, set[tuple[str, str]]] = {}
    for book_id, meta in by_id.items():
        payload = load(CORPORA / "eng_douay_rheims_1899" / str(meta.get("filename")))
        values: set[tuple[str, str]] = set()
        for chapter, verses in (payload.get("chapters") or {}).items():
            for verse in (verses or {}):
                values.add((str(chapter), str(verse)))
        refs[book_id] = values
    return book_index, refs


def source_refs(lane: str, book_id: str) -> set[tuple[str, str]]:
    if lane == "latin":
        payload = load(CORPORA / "lat_vulgate_clementine" / f"{book_id.lower()}.json")
        return {
            (str(chapter), str(verse))
            for chapter, verses in (payload.get("chapters") or {}).items()
            for verse in (verses or {})
        }
    if lane == "semitic":
        payload = load(CORPORA / "heb_arc_oshb_wlc" / "phase1a" / "surface" / f"{book_id}.json")
        return {
            (str(chapter), str(verse))
            for chapter, verses in (payload.get("chapters") or {}).items()
            for verse in (verses or {})
        }
    if lane == "greek":
        path = CORPORA / "grc_ot_catholic_full" / "sharealike" / "catholic_lxx_cc-by-sa-4.0" / "books" / f"{book_id}.json"
        require(path.exists(), f"generic Greek map currently requires complete OT Greek book payload: {book_id}")
        payload = load(path)
        return {
            (str(row.get("source_chapter")), str(row.get("source_verse")))
            for row in (payload.get("verses") or [])
            if row.get("source_chapter") is not None and row.get("source_verse") is not None
        }
    raise ValidationError(f"unsupported lane: {lane}")


def audited_mismatch_chapters(book_id: str, lane: str) -> set[str]:
    if not AUDIT.exists():
        return set()
    report = load(AUDIT)
    for row in report.get("books") or []:
        if str(row.get("id")) != book_id:
            continue
        versification = ((row.get(lane) or {}).get("versification") or {})
        return {str(item.get("chapter")) for item in versification.get("mismatches") or []}
    raise ValidationError(f"coverage audit has no book {book_id}")


def validate_segment(
    segment: dict[str, Any],
    *,
    book_id: str,
    lane: str,
    verified: bool,
    canonical_refs: set[tuple[str, str]],
    lane_refs: set[tuple[str, str]],
    seen_canonical: dict[tuple[str, str], str],
    seen_source: dict[tuple[str, str], str],
) -> None:
    segment_id = str(segment.get("id") or "").strip()
    require(segment_id, f"{book_id}/{lane}: mapping segment id is required")
    relationship = str(segment.get("relationship") or "")
    require(relationship in ALLOWED_RELATIONSHIPS, f"{book_id}/{lane}/{segment_id}: invalid relationship {relationship!r}")

    canonical_rows = segment.get("canonical_refs") or []
    source_rows = segment.get("source_refs") or []
    require(isinstance(canonical_rows, list) and isinstance(source_rows, list), f"{book_id}/{lane}/{segment_id}: refs must be lists")
    canonical = [ref_tuple(row, f"{segment_id} canonical") for row in canonical_rows]
    source = [ref_tuple(row, f"{segment_id} source") for row in source_rows]

    if relationship in {"identity", "renumber", "offset"}:
        require(canonical and source and len(canonical) == len(source), f"{segment_id}: one-to-one relationship requires equal non-empty ref counts")
    elif relationship in {"split", "merge", "range"}:
        require(canonical and source, f"{segment_id}: {relationship} requires both canonical and source refs")
    elif relationship == "component-range":
        require(canonical, f"{segment_id}: component-range requires canonical refs")
        require(source or str(segment.get("source_locus") or "").strip(), f"{segment_id}: component-range requires source refs or source_locus")
    elif relationship == "source-only":
        require(not canonical and source, f"{segment_id}: source-only must have only source refs")
    elif relationship == "canonical-only":
        require(canonical and not source, f"{segment_id}: canonical-only must have only canonical refs")

    for ref in canonical:
        require(ref in canonical_refs, f"{book_id}/{lane}/{segment_id}: canonical ref does not exist in Douay-Rheims: {ref}")
        previous = seen_canonical.get(ref)
        if previous:
            require(relationship in {"split", "merge", "range", "component-range"}, f"{segment_id}: duplicate canonical ref {ref} already used by {previous}")
        else:
            seen_canonical[ref] = segment_id
    for ref in source:
        require(ref in lane_refs, f"{book_id}/{lane}/{segment_id}: source ref does not exist in pinned corpus: {ref}")
        previous = seen_source.get(ref)
        if previous:
            require(relationship in {"split", "merge", "range", "component-range"}, f"{segment_id}: duplicate source ref {ref} already used by {previous}")
        else:
            seen_source[ref] = segment_id

    if verified:
        evidence = segment.get("evidence") or {}
        require(str(evidence.get("citation") or "").strip(), f"{book_id}/{lane}/{segment_id}: verified segment requires evidence.citation")


def validate_mapping(entry: dict[str, Any], book_index: dict[str, dict[str, Any]], canonical: dict[str, set[tuple[str, str]]]) -> None:
    book_id = str(entry.get("book_id") or "").upper()
    lane = str(entry.get("lane") or "").lower()
    status = str(entry.get("status") or "")
    filename = str(entry.get("file") or "")
    require(book_id in book_index, f"registry references unknown Catholic book {book_id}")
    require(lane in ALLOWED_LANES, f"{book_id}: invalid lane {lane}")
    require(status in ALLOWED_STATUS, f"{book_id}/{lane}: invalid registry status {status}")
    path = safe_mapping_path(filename)
    require(path.exists(), f"{book_id}/{lane}: registered mapping file missing: {filename}")
    payload = load(path)
    require(int(payload.get("schema_version") or 0) == 1, f"{filename}: unsupported schema")
    require(str(payload.get("book_id") or "").upper() == book_id, f"{filename}: book_id does not match registry")
    require(str(payload.get("lane") or "").lower() == lane, f"{filename}: lane does not match registry")
    require(str(payload.get("status") or "") == status, f"{filename}: status does not match registry")
    require(payload.get("canonical_reference_system") == "douay-rheims-1899", f"{filename}: canonical reference system changed")
    require(str(payload.get("mapping_version") or "").strip(), f"{filename}: mapping_version required")

    policy = payload.get("policy") or {}
    require(policy.get("source_text_immutable") is True, f"{filename}: source_text_immutable must be true")
    require(policy.get("fabricated_boundaries_forbidden") is True, f"{filename}: fabricated_boundaries_forbidden must be true")
    require(policy.get("bidirectional_validation_required") is True, f"{filename}: bidirectional_validation_required must be true")

    source = payload.get("source") or {}
    require(str(source.get("source_id") or "").strip(), f"{filename}: source.source_id required")
    require(str(source.get("reference_system") or "").strip(), f"{filename}: source.reference_system required")

    coverage = payload.get("coverage") or {}
    covered = {str(value) for value in coverage.get("audited_mismatch_chapters") or []}
    overrides = {str(value) for value in coverage.get("verified_override_chapters") or []}
    declared = covered | overrides
    require(not (covered & overrides), f"{filename}: audited mismatch and override chapter sets must be disjoint")
    chapters = payload.get("chapters") or []
    require(isinstance(chapters, list), f"{filename}: chapters must be a list")
    chapter_ids = {str(row.get("canonical_chapter") or "") for row in chapters}
    require("" not in chapter_ids, f"{filename}: canonical_chapter required")
    require(chapter_ids == declared, f"{filename}: chapter inventory must equal audited mismatch plus verified override chapters")

    audited = audited_mismatch_chapters(book_id, lane)
    verified = status == "verified"
    if verified:
        require(coverage.get("complete_for_audited_mismatches") is True, f"{filename}: verified mapping must declare complete audited coverage")
        require(covered == audited, f"{filename}: audited mapping coverage {sorted(covered)} does not equal structural audit mismatches {sorted(audited)}")
        require(bool(declared), f"{filename}: verified mapping must cover at least one audited mismatch or evidenced numeric-identity override")
        if overrides:
            require(coverage.get("complete_for_numeric_identity_overrides") is True, f"{filename}: override chapters require complete_for_numeric_identity_overrides=true")
            evidence = coverage.get("numeric_identity_override_evidence") or {}
            require(isinstance(evidence, dict), f"{filename}: numeric_identity_override_evidence must be an object")
            require(set(str(key) for key in evidence) == overrides, f"{filename}: override evidence keys must equal verified_override_chapters")
            for override in overrides:
                row = evidence.get(override) or {}
                require(str(row.get("citation") or "").strip(), f"{filename}: override chapter {override} requires evidence.citation")

    lane_inventory = source_refs(lane, book_id)
    seen_canonical: dict[tuple[str, str], str] = {}
    seen_source: dict[tuple[str, str], str] = {}
    for chapter in chapters:
        canonical_chapter = str(chapter.get("canonical_chapter") or "")
        require(canonical_chapter in declared, f"{filename}: chapter {canonical_chapter} not declared in coverage")
        segments = chapter.get("segments") or []
        require(isinstance(segments, list) and segments, f"{filename}: chapter {canonical_chapter} requires at least one segment")
        for segment in segments:
            validate_segment(
                segment,
                book_id=book_id,
                lane=lane,
                verified=verified,
                canonical_refs=canonical[book_id],
                lane_refs=lane_inventory,
                seen_canonical=seen_canonical,
                seen_source=seen_source,
            )


def main() -> int:
    registry = load(INDEX)
    require(int(registry.get("schema_version") or 0) == 1, "versification registry schema must be 1")
    require(registry.get("canonical_reference_system") == "douay-rheims-1899", "canonical reference system must remain Douay-Rheims 1899")
    require(str(registry.get("registry_version") or "").strip(), "registry_version required")
    policy = registry.get("policy") or {}
    for key in (
        "source_text_immutable",
        "automatic_remapping_forbidden",
        "verified_mapping_required_for_parallel_alignment",
        "bidirectional_validation_required",
        "fabricated_source_boundaries_forbidden",
    ):
        require(policy.get(key) is True, f"registry policy {key} must be true")
    require(set(registry.get("allowed_relationships") or []) == ALLOWED_RELATIONSHIPS, "registry relationship vocabulary changed unexpectedly")

    book_index, canonical = canonical_inventory()
    mappings = registry.get("mappings") or []
    require(isinstance(mappings, list), "registry mappings must be a list")
    keys: set[tuple[str, str]] = set()
    files: set[str] = set()
    for entry in mappings:
        key = (str(entry.get("book_id") or "").upper(), str(entry.get("lane") or "").lower())
        require(key not in keys, f"duplicate versification registry key: {key}")
        keys.add(key)
        filename = str(entry.get("file") or "")
        require(filename not in files, f"mapping file registered twice: {filename}")
        files.add(filename)
        validate_mapping(entry, book_index, canonical)

    print(
        "Logos versification registry validation passed: "
        f"{len(mappings)} mapping file(s), "
        f"{sum(1 for row in mappings if row.get('status') == 'verified')} verified"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as exc:
        raise SystemExit(f"Logos versification validation failed: {exc}") from exc
