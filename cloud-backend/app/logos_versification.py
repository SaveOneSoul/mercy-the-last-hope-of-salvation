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


def canonical_source_mapping(
    book_id: str,
    lane: str,
    canonical_chapter: int | str,
    canonical_verse: int | str,
) -> dict[str, Any] | None:
    """Resolve one canonical verse through a verified map without altering source boundaries."""
    chapter = str(canonical_chapter)
    verse = str(canonical_verse)
    wanted = (chapter, verse)
    status = mapping_status(book_id, lane, chapter)
    if status.get("status") != "verified-map":
        return None

    for segment in canonical_segments(book_id, lane, chapter):
        relationship = str(segment.get("relationship") or "")
        canonical_rows = list(segment.get("canonical_refs") or [])
        source_rows = list(segment.get("source_refs") or [])
        canonical_refs = [(str(row.get("chapter")), str(row.get("verse"))) for row in canonical_rows]
        if wanted not in canonical_refs:
            continue

        selected: list[dict[str, str]] = []
        if relationship in {"identity", "renumber", "offset"}:
            if len(canonical_rows) != len(source_rows):
                raise RuntimeError("Verified one-to-one mapping has unequal reference counts")
            idx = canonical_refs.index(wanted)
            row = source_rows[idx]
            selected = [{"chapter": str(row.get("chapter")), "verse": str(row.get("verse"))}]
        elif relationship == "merge":
            if len(canonical_rows) != 1 or not source_rows:
                raise RuntimeError("Verified merge mapping must map one canonical ref to source refs")
            selected = [{"chapter": str(row.get("chapter")), "verse": str(row.get("verse"))} for row in source_rows]
        elif relationship == "split":
            if len(source_rows) != 1 or not canonical_rows:
                raise RuntimeError("Verified split mapping must map canonical refs to one source ref")
            row = source_rows[0]
            selected = [{"chapter": str(row.get("chapter")), "verse": str(row.get("verse"))}]
        elif relationship in {"range", "component-range"}:
            if len(canonical_rows) == len(source_rows) and source_rows:
                idx = canonical_refs.index(wanted)
                row = source_rows[idx]
                selected = [{"chapter": str(row.get("chapter")), "verse": str(row.get("verse"))}]
            else:
                raise RuntimeError("Ambiguous verified range mapping requires a lane-specific resolver")
        elif relationship == "canonical-only":
            selected = []
        else:
            return None

        return {
            "book_id": str(book_id).upper(),
            "lane": str(lane).lower(),
            "canonical_ref": {"chapter": chapter, "verse": verse},
            "relationship": relationship,
            "segment_id": segment.get("id"),
            "source_refs": selected,
            "mapping_version": status.get("mapping_version"),
            "mapping_file": status.get("file"),
        }
    return None
