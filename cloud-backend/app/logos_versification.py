import json
from functools import lru_cache
from pathlib import Path
from typing import Any

REGISTRY_ROOT = Path(__file__).with_name("logos_interlinear") / "versification"
REGISTRY_PATH = REGISTRY_ROOT / "index.json"
ALLOWED_LANES = {"semitic", "greek", "latin"}


@lru_cache(maxsize=1)
def _registry() -> dict[str, Any]:
    if not REGISTRY_PATH.exists():
        return {}
    payload = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    if int(payload.get("schema_version") or 0) != 1:
        raise RuntimeError("Unsupported Logos versification registry schema")
    if payload.get("canonical_reference_system") != "douay-rheims-1899":
        raise RuntimeError("Unexpected Logos canonical versification system")
    return payload


def _safe_mapping_path(value: str) -> Path:
    relative = Path(str(value))
    if relative.is_absolute() or ".." in relative.parts or not relative.parts:
        raise RuntimeError("Invalid Logos versification mapping path")
    path = (REGISTRY_ROOT / relative).resolve()
    root = REGISTRY_ROOT.resolve()
    if root not in path.parents:
        raise RuntimeError("Versification mapping escapes registry root")
    if path.suffix.lower() != ".json":
        raise RuntimeError("Versification mapping must be JSON")
    return path


@lru_cache(maxsize=128)
def _mapping_document(filename: str) -> dict[str, Any]:
    path = _safe_mapping_path(filename)
    if not path.exists():
        raise RuntimeError(f"Registered Logos versification mapping is missing: {filename}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if int(payload.get("schema_version") or 0) != 1:
        raise RuntimeError(f"Unsupported versification mapping schema: {filename}")
    return payload


def registry_summary() -> dict[str, Any]:
    registry = _registry()
    mappings = list(registry.get("mappings") or [])
    verified = [row for row in mappings if row.get("status") == "verified"]
    draft = [row for row in mappings if row.get("status") == "draft"]
    return {
        "installed": bool(registry),
        "schema_version": registry.get("schema_version"),
        "registry_version": registry.get("registry_version"),
        "canonical_reference_system": registry.get("canonical_reference_system"),
        "registered_mapping_count": len(mappings),
        "verified_mapping_count": len(verified),
        "draft_mapping_count": len(draft),
        "verified_book_count": len({str(row.get("book_id")) for row in verified}),
        "policy": registry.get("policy") or {},
    }


def _entry_for(book_id: str, lane: str) -> dict[str, Any] | None:
    lane = str(lane).lower()
    if lane not in ALLOWED_LANES:
        raise ValueError(f"Unsupported Logos versification lane: {lane}")
    wanted_book = str(book_id).upper()
    for row in _registry().get("mappings") or []:
        if str(row.get("book_id")).upper() == wanted_book and str(row.get("lane")).lower() == lane:
            return row
    return None


def mapping_status(book_id: str, lane: str, canonical_chapter: int | str | None = None) -> dict[str, Any]:
    entry = _entry_for(book_id, lane)
    if not entry:
        return {
            "status": "unresolved",
            "book_id": str(book_id).upper(),
            "lane": str(lane).lower(),
            "registered": False,
            "verified": False,
        }

    filename = str(entry.get("file") or "")
    document = _mapping_document(filename)
    status = str(document.get("status") or entry.get("status") or "draft")
    coverage = document.get("coverage") or {}
    covered = {str(value) for value in coverage.get("audited_mismatch_chapters") or []}
    chapter = str(canonical_chapter) if canonical_chapter is not None else None
    chapter_covered = chapter is None or chapter in covered
    verified = (
        status == "verified"
        and entry.get("status") == "verified"
        and coverage.get("complete_for_audited_mismatches") is True
    )
    return {
        "status": "verified-map" if verified and chapter_covered else ("draft-map" if status == "draft" else "unresolved"),
        "book_id": str(book_id).upper(),
        "lane": str(lane).lower(),
        "registered": True,
        "verified": bool(verified),
        "chapter_covered": bool(chapter_covered),
        "mapping_version": document.get("mapping_version"),
        "file": filename,
        "source": document.get("source") or {},
        "coverage": coverage,
    }


def mapping_document(book_id: str, lane: str) -> dict[str, Any] | None:
    entry = _entry_for(book_id, lane)
    if not entry:
        return None
    return _mapping_document(str(entry.get("file") or ""))


def canonical_segments(book_id: str, lane: str, canonical_chapter: int | str) -> list[dict[str, Any]]:
    status = mapping_status(book_id, lane, canonical_chapter)
    if status.get("status") != "verified-map":
        return []
    document = mapping_document(book_id, lane) or {}
    wanted = str(canonical_chapter)
    for chapter in document.get("chapters") or []:
        if str(chapter.get("canonical_chapter")) == wanted:
            return list(chapter.get("segments") or [])
    return []


def canonical_source_map(book_id: str, lane: str, canonical_chapter: int | str) -> dict[str, Any]:
    """Return an explicit canonical-verse -> source-ref map for safe generic relationships.

    This helper never edits source text and never guesses a mapping. Component/range mappings that
    cannot be represented without a specialized adapter are deliberately reported unsupported.
    """
    status = mapping_status(book_id, lane, canonical_chapter)
    if status.get("status") != "verified-map":
        return {"supported": False, "reason": "verified-map-required", "status": status, "verses": {}}

    verses: dict[str, dict[str, Any]] = {}
    for segment in canonical_segments(book_id, lane, canonical_chapter):
        segment_id = str(segment.get("id") or "")
        relationship = str(segment.get("relationship") or "")
        canonical_refs = list(segment.get("canonical_refs") or [])
        source_refs = list(segment.get("source_refs") or [])

        pairs: list[tuple[dict[str, Any], list[dict[str, Any]]]] = []
        if relationship in {"identity", "renumber", "offset"}:
            if not canonical_refs or len(canonical_refs) != len(source_refs):
                return {"supported": False, "reason": "invalid-one-to-one-segment", "segment_id": segment_id, "status": status, "verses": {}}
            pairs = [(canonical, [source]) for canonical, source in zip(canonical_refs, source_refs)]
        elif relationship == "split":
            if len(canonical_refs) != 1 or not source_refs:
                return {"supported": False, "reason": "split-requires-one-canonical-ref", "segment_id": segment_id, "status": status, "verses": {}}
            pairs = [(canonical_refs[0], source_refs)]
        elif relationship == "merge":
            if not canonical_refs or len(source_refs) != 1:
                return {"supported": False, "reason": "merge-requires-one-source-ref", "segment_id": segment_id, "status": status, "verses": {}}
            pairs = [(canonical, source_refs) for canonical in canonical_refs]
        elif relationship == "canonical-only":
            pairs = [(canonical, []) for canonical in canonical_refs]
        else:
            return {"supported": False, "reason": f"specialized-adapter-required:{relationship}", "segment_id": segment_id, "status": status, "verses": {}}

        for canonical, sources in pairs:
            if str(canonical.get("chapter")) != str(canonical_chapter):
                return {"supported": False, "reason": "cross-chapter-canonical-segment", "segment_id": segment_id, "status": status, "verses": {}}
            verse = str(canonical.get("verse") or "")
            if not verse or verse in verses:
                return {"supported": False, "reason": "duplicate-or-empty-canonical-verse", "segment_id": segment_id, "status": status, "verses": {}}
            verses[verse] = {
                "segment_id": segment_id,
                "relationship": relationship,
                "source_refs": [
                    {"chapter": str(source.get("chapter")), "verse": str(source.get("verse"))}
                    for source in sources
                ],
            }

    return {
        "supported": bool(verses),
        "reason": None if verses else "no-mapped-verses",
        "status": status,
        "verses": verses,
    }
