import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _corpus_book, _corpus_manifest, _parse_corpus_reference

router = APIRouter(prefix="/ot-lxx", tags=["Logos Full Septuagint Old Testament"])
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "grc_ot_swete_full"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
ISOLATED_ROOT = CORPUS_DIR / "sharealike" / "first1kgreek_swete_cc-by-sa-4.0"
BOOK_DIR = ISOLATED_ROOT / "books"
EXPECTED_SOURCE_COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
EXPECTED_TREE_SHA = "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79"


@lru_cache(maxsize=1)
def _manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if payload.get("corpus_id") != "grc_ot_swete_full" or payload.get("production_enabled") is not True:
        raise RuntimeError("Unexpected Logos full Swete OT manifest")
    if int(payload.get("book_count") or 0) != 39:
        raise RuntimeError("Full Swete OT package does not contain 39 protocanonical Catholic book scopes")
    source = payload.get("source") or {}
    if source.get("commit") != EXPECTED_SOURCE_COMMIT or source.get("septuagint_tree_sha") != EXPECTED_TREE_SHA:
        raise RuntimeError("Full Swete OT immutable source pin changed")
    if source.get("license") != "CC BY-SA 4.0" or source.get("share_alike") is not True or source.get("isolation_required") is not True:
        raise RuntimeError("Full Swete OT rights/isolation contract changed")
    partition = payload.get("partition") or {}
    if partition.get("share_alike") is not True or partition.get("isolation_required") is not True:
        raise RuntimeError("Full Swete OT ShareAlike partition contract changed")
    return payload


@lru_cache(maxsize=64)
def _book(book_id: str) -> dict:
    safe = "".join(ch for ch in str(book_id).upper() if ch.isalnum())
    if safe != str(book_id).upper():
        raise RuntimeError("Invalid full Swete OT book id")
    path = BOOK_DIR / f"{safe}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="logos_full_lxx_book_not_installed")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("book_id") != safe or payload.get("corpus_id") != "grc_ot_swete_full":
        raise RuntimeError("Unexpected full Swete OT book payload")
    if payload.get("license") != "CC BY-SA 4.0" or payload.get("share_alike") is not True or payload.get("isolation_required") is not True:
        raise RuntimeError("Full Swete OT book rights/isolation contract changed")
    if (payload.get("source") or {}).get("per_file_license_verified") is not True:
        raise RuntimeError("Full Swete OT per-file licence gate missing")
    return payload


def _dra_book_meta(book_id: str) -> dict:
    for row in _corpus_manifest().get("books") or []:
        if str(row.get("id")) == book_id:
            return row
    raise HTTPException(status_code=404, detail="logos_book_not_in_catholic_canon")


def _canonical_reference(book: str, chapter: int, verse_start: int | None, verse_end: int | None) -> str:
    if verse_start is None:
        return f"{book} {chapter}"
    if verse_end is not None and verse_end != verse_start:
        return f"{book} {chapter}:{verse_start}-{verse_end}"
    return f"{book} {chapter}:{verse_start}"


def _source_chapter_for(book: dict, canonical_chapter: int) -> str:
    mapping = book.get("mapping") or {}
    offset = int(mapping.get("canonical_chapter_offset") or 0)
    return str(canonical_chapter + offset)


def _source_rows_for_chapter(book: dict, canonical_chapter: int) -> list[dict]:
    source_chapter = _source_chapter_for(book, canonical_chapter)
    return [row for row in (book.get("verses") or []) if str(row.get("source_chapter")) == source_chapter]


def _numeric_source_rows(rows: list[dict]) -> dict[int, dict] | None:
    output: dict[int, dict] = {}
    for row in rows:
        source_verse = str(row.get("source_verse") or "")
        if not source_verse.isdigit():
            return None
        number = int(source_verse)
        if number in output:
            return None
        output[number] = row
    return output


def _numeric_dra_keys(chapter: dict) -> set[int] | None:
    output: set[int] = set()
    for key in chapter:
        text = str(key)
        if not text.isdigit():
            return None
        output.add(int(text))
    return output


def _chapter_identity(book_id: str, chapter: int, source_book: dict) -> dict:
    rows = _source_rows_for_chapter(source_book, chapter)
    source_map = _numeric_source_rows(rows)
    dra_meta = _dra_book_meta(book_id)
    dra_book = _corpus_book(str(dra_meta.get("filename")))
    dra_chapter = (dra_book.get("chapters") or {}).get(str(chapter)) or {}
    dra_set = _numeric_dra_keys(dra_chapter)
    source_set = set(source_map) if source_map is not None else None
    exact = bool(rows and dra_chapter and source_set is not None and dra_set is not None and source_set == dra_set)
    return {
        "exact": exact,
        "mode": "exact-dra-swete-chapter-verse-identity" if exact else "explicit-mapping-required",
        "canonical_chapter": chapter,
        "source_chapter": _source_chapter_for(source_book, chapter),
        "source_verse_count": len(rows),
        "dra_verse_count": len(dra_chapter),
        "automatic_remapping": False,
        "source_boundary_preserved": True,
    }


def _public_row(row: dict) -> dict:
    return {
        "source_chapter": row.get("source_chapter"),
        "source_verse": row.get("source_verse"),
        "source_reference": row.get("source_reference"),
        "surface": row.get("surface"),
    }


def _study_payload(reference: str) -> dict:
    manifest = _manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="logos_full_lxx_corpus_not_installed")
    book_meta, chapter, verse_start, verse_end = _parse_corpus_reference(reference)
    if str(book_meta.get("testament")) != "OT":
        raise HTTPException(status_code=404, detail="logos_full_lxx_ot_reference_required")
    book_id = str(book_meta.get("id"))
    supported = {str(row.get("book_id")) for row in (manifest.get("books") or [])}
    if book_id not in supported:
        raise HTTPException(status_code=404, detail="logos_full_lxx_reference_not_in_protocanonical_scope")

    source_book = _book(book_id)
    alignment = _chapter_identity(book_id, chapter, source_book)
    canonical_ref = _canonical_reference(str(book_meta.get("name")), chapter, verse_start, verse_end)
    if alignment.get("exact") is not True:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "logos_full_lxx_versification_mapping_required",
                "reference": canonical_ref,
                "alignment": alignment,
                "message": "The Swete Greek witness is installed, but this chapter is not rendered verse-for-verse against Douay-Rheims until an explicit versification mapping is validated.",
            },
        )

    rows = _source_rows_for_chapter(source_book, chapter)
    numeric = _numeric_source_rows(rows)
    if numeric is None:
        raise HTTPException(status_code=409, detail="logos_full_lxx_non_numeric_source_versification")
    if verse_start is None:
        numbers = sorted(numeric)
    else:
        numbers = list(range(verse_start, (verse_end or verse_start) + 1))
    selected = []
    for number in numbers:
        row = numeric.get(number)
        if row is None:
            raise HTTPException(status_code=404, detail="logos_full_lxx_source_verse_not_found")
        selected.append(_public_row(row))

    return {
        "reference": canonical_ref,
        "book": book_meta.get("name"),
        "book_id": book_id,
        "chapter": chapter,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "language": "grc",
        "label": "Septuagint — Swete",
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "license": source_book.get("license"),
        "share_alike": source_book.get("share_alike"),
        "isolation_required": source_book.get("isolation_required"),
        "alignment": alignment,
        "mapping": source_book.get("mapping") or {},
        "verses": selected,
        "source": source_book.get("source") or {},
        "derived_layers": manifest.get("derived_layers") or {},
        "note": "The Greek source surface is preserved from the pinned Swete witness. No LXX gloss, lemma, morphology, transliteration or verse remapping is fabricated.",
    }


@router.get("/catalog")
def catalog(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _manifest()
    return {
        "installed": bool(manifest),
        "production_enabled": manifest.get("production_enabled", False),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "book_count": manifest.get("book_count", 0),
        "verse_record_count": manifest.get("verse_record_count", 0),
        "scope": manifest.get("scope"),
        "source": manifest.get("source") or {},
    }


@router.get("/source-rights")
def source_rights(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="logos_full_lxx_corpus_not_installed")
    return {
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "source": manifest.get("source") or {},
        "partition": manifest.get("partition") or {},
        "runtime_contract": manifest.get("runtime_contract") or {},
        "derived_layers": manifest.get("derived_layers") or {},
    }


@router.get("/interlinear")
def interlinear(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    return _study_payload(reference)
