import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _corpus_book, _corpus_manifest, _parse_corpus_reference

router = APIRouter(prefix="/ot-lxx", tags=["Logos Complete Protocanonical Greek Old Testament"])
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "grc_ot_catholic_full"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
ISOLATED_ROOT = CORPUS_DIR / "sharealike" / "catholic_lxx_cc-by-sa-4.0"
BOOK_DIR = ISOLATED_ROOT / "books"
FIRST1K_COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
FIRST1K_TREE_SHA = "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79"
ECC_COMMIT = "338aa27310b3cfe2588a993b4d113b503597d70f"
ECC_BLOB = "1659770789d318e7ee04f3ee03684bf880922bc4"


@lru_cache(maxsize=1)
def _manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if payload.get("corpus_id") != "grc_ot_catholic_full" or payload.get("production_enabled") is not True:
        raise RuntimeError("Unexpected Logos complete Catholic Greek OT manifest")
    if int(payload.get("book_count") or 0) != 39:
        raise RuntimeError("Complete Catholic Greek OT package does not contain 39 protocanonical book scopes")
    if int(payload.get("first1k_swete_book_scope_count") or 0) != 38:
        raise RuntimeError("Complete Catholic Greek OT package does not preserve 38 First1K/Swete scopes")
    if int(payload.get("ecclesiastes_fallback_book_scope_count") or 0) != 1:
        raise RuntimeError("Complete Catholic Greek OT package lacks the explicit Ecclesiastes fallback scope")
    sources = payload.get("sources") or {}
    first1k = sources.get("first1k_swete") or {}
    if first1k.get("commit") != FIRST1K_COMMIT or first1k.get("septuagint_tree_sha") != FIRST1K_TREE_SHA:
        raise RuntimeError("Complete Catholic Greek OT First1K immutable source pin changed")
    ecclesiastes = sources.get("ecclesiastes") or {}
    if ecclesiastes.get("commit") != ECC_COMMIT or ecclesiastes.get("git_blob_sha1") != ECC_BLOB:
        raise RuntimeError("Complete Catholic Greek OT Ecclesiastes immutable source pin changed")
    if ecclesiastes.get("first1k_gap_verified") is not True:
        raise RuntimeError("Complete Catholic Greek OT Ecclesiastes fallback no longer proves the First1K gap")
    if first1k.get("license") != "CC BY-SA 4.0" or ecclesiastes.get("license") != "CC BY-SA 4.0":
        raise RuntimeError("Complete Catholic Greek OT source licence contract changed")
    partition = payload.get("partition") or {}
    if partition.get("share_alike") is not True or partition.get("isolation_required") is not True:
        raise RuntimeError("Complete Catholic Greek OT ShareAlike partition contract changed")
    runtime = payload.get("runtime_contract") or {}
    if runtime.get("source_boundaries_preserved") is not True or runtime.get("empty_source_divisions_preserved") is not True:
        raise RuntimeError("Complete Catholic Greek OT source-boundary preservation contract changed")
    if runtime.get("ecclesiastes_not_swete") is not True:
        raise RuntimeError("Ecclesiastes must remain explicitly distinguished from Swete")
    return payload


@lru_cache(maxsize=64)
def _book(book_id: str) -> dict:
    safe = "".join(ch for ch in str(book_id).upper() if ch.isalnum())
    if safe != str(book_id).upper():
        raise RuntimeError("Invalid complete Catholic Greek OT book id")
    path = BOOK_DIR / f"{safe}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="logos_full_lxx_book_not_installed")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("book_id") != safe or payload.get("corpus_id") != "grc_ot_catholic_full":
        raise RuntimeError("Unexpected complete Catholic Greek OT book payload")
    if payload.get("license") != "CC BY-SA 4.0" or payload.get("share_alike") is not True or payload.get("isolation_required") is not True:
        raise RuntimeError("Complete Catholic Greek OT book rights/isolation contract changed")
    source = payload.get("source") or {}
    if source.get("per_file_license_verified") is not True:
        raise RuntimeError("Complete Catholic Greek OT per-file licence gate missing")
    if safe == "ECC":
        if source.get("source_family") != "open-greek-wikisource-ecclesiastes":
            raise RuntimeError("Ecclesiastes source family changed")
        if source.get("commit") != ECC_COMMIT or source.get("git_blob_sha1") != ECC_BLOB:
            raise RuntimeError("Ecclesiastes source integrity pin changed")
    else:
        if source.get("source_family") != "first1k-swete":
            raise RuntimeError(f"{safe} unexpectedly left the First1K/Swete source family")
        if source.get("commit") != FIRST1K_COMMIT:
            raise RuntimeError(f"{safe} First1K source pin changed")
    surface_policy = payload.get("surface_policy") or {}
    if surface_policy.get("source_boundaries_preserved") is not True or surface_policy.get("empty_source_divisions_preserved") is not True:
        raise RuntimeError("Complete Catholic Greek OT source-surface preservation metadata missing")
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
        "mode": "exact-dra-greek-chapter-verse-identity" if exact else "explicit-mapping-required",
        "canonical_chapter": chapter,
        "source_chapter": _source_chapter_for(source_book, chapter),
        "source_verse_count": len(rows),
        "dra_verse_count": len(dra_chapter),
        "empty_source_surface_count": sum(1 for row in rows if row.get("source_empty_surface") is True),
        "automatic_remapping": False,
        "source_boundary_preserved": True,
        "empty_source_divisions_preserved": True,
    }


def _public_row(row: dict) -> dict:
    return {
        "source_chapter": row.get("source_chapter"),
        "source_verse": row.get("source_verse"),
        "source_reference": row.get("source_reference"),
        "surface": row.get("surface"),
        "source_empty_surface": row.get("source_empty_surface") is True,
    }


def _label(source_book: dict) -> str:
    source = source_book.get("source") or {}
    if source.get("source_family") == "open-greek-wikisource-ecclesiastes":
        return "Septuagint — Greek Wikisource Ecclesiastes"
    return "Septuagint — Swete"


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
                "message": "The Greek OT witness is installed, but this chapter is not rendered verse-for-verse against Douay-Rheims until an explicit versification mapping is validated.",
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

    source = source_book.get("source") or {}
    source_family = source.get("source_family")
    note = (
        "Ecclesiastes is served from the pinned Greek Wikisource ecclesiastical LXX fallback because the pinned First1K tree contains only its CTS stub. Native source numbering is preserved; this witness is not represented as Swete."
        if source_family == "open-greek-wikisource-ecclesiastes"
        else "The Greek source surface and verse divisions are preserved from the pinned Swete witness, including explicitly empty source divisions."
    )
    return {
        "reference": canonical_ref,
        "book": book_meta.get("name"),
        "book_id": book_id,
        "chapter": chapter,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "language": "grc",
        "label": _label(source_book),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "license": source_book.get("license"),
        "share_alike": source_book.get("share_alike"),
        "isolation_required": source_book.get("isolation_required"),
        "alignment": alignment,
        "mapping": source_book.get("mapping") or {},
        "verses": selected,
        "source": source,
        "derived_layers": manifest.get("derived_layers") or {},
        "note": note + " No LXX gloss, lemma, morphology, transliteration or verse remapping is fabricated.",
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
        "first1k_swete_book_scope_count": manifest.get("first1k_swete_book_scope_count", 0),
        "ecclesiastes_fallback_book_scope_count": manifest.get("ecclesiastes_fallback_book_scope_count", 0),
        "verse_record_count": manifest.get("verse_record_count", 0),
        "empty_source_surface_count": manifest.get("empty_source_surface_count", 0),
        "scope": manifest.get("scope"),
        "sources": manifest.get("sources") or {},
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
        "sources": manifest.get("sources") or {},
        "partition": manifest.get("partition") or {},
        "runtime_contract": manifest.get("runtime_contract") or {},
        "derived_layers": manifest.get("derived_layers") or {},
        "empty_source_surfaces": manifest.get("empty_source_surfaces") or [],
    }


@router.get("/interlinear")
def interlinear(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    return _study_payload(reference)
