import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _corpus_book, _corpus_manifest, _parse_corpus_reference
from .logos_versification import canonical_source_map

router = APIRouter(prefix="/ot-latin", tags=["Logos Clementine Vulgate"])
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "lat_vulgate_clementine"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
EXPECTED_SOURCE_COMMIT = "f257a3559025c3f873b48a75019f53a9354ed7de"
EXPECTED_SOURCE_BLOB = "c0e65106383658fd914e90da4c82f2be48a0a762"


@lru_cache(maxsize=1)
def _manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if payload.get("corpus_id") != "lat_vulgate_clementine" or payload.get("production_enabled") is not True:
        raise RuntimeError("Unexpected Logos Clementine Vulgate manifest")
    if int(payload.get("book_count") or 0) != 73:
        raise RuntimeError("Clementine Vulgate corpus is not the complete Catholic canon")
    source = payload.get("source") or {}
    if source.get("commit") != EXPECTED_SOURCE_COMMIT or source.get("git_blob_sha1") != EXPECTED_SOURCE_BLOB:
        raise RuntimeError("Clementine Vulgate immutable source pin changed")
    if source.get("rights") != "public-domain" or source.get("license") != "Public Domain":
        raise RuntimeError("Clementine Vulgate rights gate changed")
    return payload


@lru_cache(maxsize=128)
def _book(book_id: str) -> dict:
    safe = "".join(ch for ch in str(book_id).upper() if ch.isalnum())
    if safe != str(book_id).upper():
        raise RuntimeError("Invalid Vulgate book id")
    path = CORPUS_DIR / f"{safe.lower()}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="logos_vulgate_book_not_installed")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("book_id") != safe or payload.get("corpus_id") != "lat_vulgate_clementine":
        raise RuntimeError("Unexpected Vulgate book payload")
    return payload


def _dra_book_meta(book_id: str) -> dict:
    for row in _corpus_manifest().get("books") or []:
        if str(row.get("id")) == book_id:
            return row
    raise HTTPException(status_code=404, detail="logos_book_not_in_catholic_canon")


def _dra_chapter(book_id: str, chapter: int) -> dict:
    meta = _dra_book_meta(book_id)
    dra = _corpus_book(str(meta.get("filename")))
    rows = (dra.get("chapters") or {}).get(str(chapter)) or {}
    if not rows:
        raise HTTPException(status_code=404, detail="logos_chapter_not_found")
    return rows


def _numeric_keys(chapter: dict) -> set[int] | None:
    out: set[int] = set()
    for key in chapter:
        if not str(key).isdigit():
            return None
        out.add(int(key))
    return out


def _chapter_identity(book_id: str, chapter: int, latin: dict) -> dict:
    source_chapter = (latin.get("chapters") or {}).get(str(chapter)) or {}
    dra_chapter = _dra_chapter(book_id, chapter)
    source_set = _numeric_keys(source_chapter)
    dra_set = _numeric_keys(dra_chapter)
    exact = bool(source_chapter and dra_chapter and source_set is not None and dra_set is not None and source_set == dra_set)
    return {
        "exact": exact,
        "mode": "exact-dra-vulgate-chapter-verse-identity" if exact else "explicit-mapping-required",
        "source_verse_count": len(source_chapter),
        "dra_verse_count": len(dra_chapter),
        "automatic_remapping": False,
    }


def _reference(book: str, chapter: int, start: int | None, end: int | None) -> str:
    if start is None:
        return f"{book} {chapter}"
    if end is not None and end != start:
        return f"{book} {chapter}:{start}-{end}"
    return f"{book} {chapter}:{start}"


def _canonical_numbers(book_id: str, chapter: int, start: int | None, end: int | None) -> list[int]:
    dra_chapter = _dra_chapter(book_id, chapter)
    if start is None:
        if any(not str(value).isdigit() for value in dra_chapter):
            raise RuntimeError("Mapped Vulgate runtime currently requires numeric Douay verse ids")
        return sorted(int(value) for value in dra_chapter)
    return list(range(start, (end or start) + 1))


def _mapped_chapter_rows(
    book_id: str,
    chapter: int,
    verse_start: int | None,
    verse_end: int | None,
    latin: dict,
) -> tuple[dict, list[dict]] | None:
    mapping = canonical_source_map(book_id, "latin", chapter)
    if mapping.get("supported") is not True:
        return None

    mapping_rows = mapping.get("verses") or {}
    verses: list[dict] = []
    for canonical_number in _canonical_numbers(book_id, chapter, verse_start, verse_end):
        mapped = mapping_rows.get(str(canonical_number))
        if not mapped:
            raise RuntimeError(
                f"Verified Latin versification map omitted canonical {book_id} {chapter}:{canonical_number}"
            )

        source_verses: list[dict] = []
        surface_parts: list[str] = []
        for source_ref in mapped.get("source_refs") or []:
            source_chapter = str(source_ref.get("chapter"))
            source_verse = str(source_ref.get("verse"))
            source_rows = (latin.get("chapters") or {}).get(source_chapter) or {}
            surface = source_rows.get(source_verse)
            if surface is None:
                raise RuntimeError(
                    f"Verified Latin versification map points to missing source {book_id} {source_chapter}:{source_verse}"
                )
            source_verses.append(
                {
                    "chapter": int(source_chapter) if source_chapter.isdigit() else source_chapter,
                    "verse": int(source_verse) if source_verse.isdigit() else source_verse,
                    "surface": surface,
                }
            )
            surface_parts.append(surface)

        verses.append(
            {
                "verse": canonical_number,
                "surface": " ".join(surface_parts),
                "relationship": mapped.get("relationship"),
                "segment_id": mapped.get("segment_id"),
                "source_refs": [
                    {"chapter": row["chapter"], "verse": row["verse"]}
                    for row in source_verses
                ],
                "source_verses": source_verses,
            }
        )

    status = mapping.get("status") or {}
    source_chapter = (latin.get("chapters") or {}).get(str(chapter)) or {}
    alignment = {
        "exact": False,
        "mode": "verified-dra-vulgate-explicit-map",
        "source_verse_count": len(source_chapter),
        "dra_verse_count": len(_dra_chapter(book_id, chapter)),
        "automatic_remapping": False,
        "verified_registry_mapping": True,
        "mapping_version": status.get("mapping_version"),
        "mapping_file": status.get("file"),
        "source_boundaries_preserved": True,
    }
    return alignment, verses


def _study_payload(reference: str) -> dict:
    manifest = _manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="logos_vulgate_corpus_not_installed")
    book_meta, chapter, verse_start, verse_end = _parse_corpus_reference(reference)
    book_id = str(book_meta.get("id"))
    latin = _book(book_id)
    alignment = _chapter_identity(book_id, chapter, latin)
    canonical_ref = _reference(str(book_meta.get("name")), chapter, verse_start, verse_end)

    if alignment.get("exact") is True:
        chapter_rows = (latin.get("chapters") or {}).get(str(chapter)) or {}
        numbers = (
            sorted(int(x) for x in chapter_rows)
            if verse_start is None
            else list(range(verse_start, (verse_end or verse_start) + 1))
        )
        verses = []
        for number in numbers:
            text = chapter_rows.get(str(number))
            if text is None:
                raise HTTPException(status_code=404, detail="logos_vulgate_verse_not_found")
            verses.append({"verse": number, "surface": text})
    else:
        mapped = _mapped_chapter_rows(book_id, chapter, verse_start, verse_end, latin)
        if mapped is None:
            raise HTTPException(
                status_code=409,
                detail={
                    "code": "logos_vulgate_versification_mapping_required",
                    "reference": canonical_ref,
                    "alignment": alignment,
                    "message": "The Clementine witness is installed, but this chapter is not rendered in parallel until its Douay-Rheims verse identity is explicitly verified.",
                },
            )
        alignment, verses = mapped

    return {
        "reference": canonical_ref,
        "book": book_meta.get("name"),
        "book_id": book_id,
        "chapter": chapter,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "language": "la",
        "label": "Clementine Latin Vulgate",
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "alignment": alignment,
        "verses": verses,
        "source": manifest.get("source") or {},
        "derived_layers": manifest.get("derived_layers") or {},
        "note": "The Latin surface is served locally from the pinned public-domain Clementine corpus. Verified registry mappings preserve every source verse boundary explicitly; no Latin lemma, morphology, gloss, transliteration, or synthetic verse boundary is fabricated.",
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
        "chapter_count": manifest.get("chapter_count", 0),
        "verse_count": manifest.get("verse_count", 0),
        "source": manifest.get("source") or {},
    }


@router.get("/source-rights")
def source_rights(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="logos_vulgate_corpus_not_installed")
    return {
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "source": manifest.get("source") or {},
        "runtime_contract": manifest.get("runtime_contract") or {},
        "derived_layers": manifest.get("derived_layers") or {},
    }


@router.get("/interlinear")
def interlinear(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    return _study_payload(reference)
