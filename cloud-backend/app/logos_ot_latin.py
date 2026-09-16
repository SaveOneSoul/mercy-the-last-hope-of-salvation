import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _corpus_book, _corpus_manifest, _parse_corpus_reference
from .logos_versification import canonical_source_mapping, mapping_status

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
    return (dra.get("chapters") or {}).get(str(chapter)) or {}


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
    registry = mapping_status(book_id, "latin", chapter) if not exact else None
    verified_map = bool(registry and registry.get("status") == "verified-map")
    return {
        "exact": exact,
        "verified_mapping": verified_map,
        "mode": (
            "exact-dra-vulgate-chapter-verse-identity"
            if exact
            else "verified-explicit-map"
            if verified_map
            else "explicit-mapping-required"
        ),
        "source_verse_count": len(source_chapter),
        "dra_verse_count": len(dra_chapter),
        "automatic_remapping": False,
        "mapping": registry if verified_map else None,
    }


def _reference(book: str, chapter: int, start: int | None, end: int | None) -> str:
    if start is None:
        return f"{book} {chapter}"
    if end is not None and end != start:
        return f"{book} {chapter}:{start}-{end}"
    return f"{book} {chapter}:{start}"


def _source_rows(latin: dict, refs: list[dict]) -> list[dict]:
    rows: list[dict] = []
    chapters = latin.get("chapters") or {}
    for ref in refs:
        chapter = str(ref.get("chapter"))
        verse = str(ref.get("verse"))
        text = (chapters.get(chapter) or {}).get(verse)
        if text is None:
            raise RuntimeError(f"Verified Vulgate mapping references missing source verse {chapter}:{verse}")
        rows.append({"chapter": int(chapter), "verse": int(verse), "surface": text})
    return rows


def _study_payload(reference: str) -> dict:
    manifest = _manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="logos_vulgate_corpus_not_installed")
    book_meta, chapter, verse_start, verse_end = _parse_corpus_reference(reference)
    book_id = str(book_meta.get("id"))
    latin = _book(book_id)
    alignment = _chapter_identity(book_id, chapter, latin)
    canonical_ref = _reference(str(book_meta.get("name")), chapter, verse_start, verse_end)
    if alignment.get("exact") is not True and alignment.get("verified_mapping") is not True:
        raise HTTPException(status_code=409, detail={
            "code": "logos_vulgate_versification_mapping_required",
            "reference": canonical_ref,
            "alignment": alignment,
            "message": "The Clementine witness is installed, but this chapter is not rendered in parallel until its Douay-Rheims verse identity is explicitly verified.",
        })

    dra_chapter = _dra_chapter(book_id, chapter)
    if not dra_chapter:
        raise HTTPException(status_code=404, detail="logos_douay_chapter_not_found")
    if verse_start is None:
        numbers = sorted(int(x) for x in dra_chapter)
    else:
        numbers = list(range(verse_start, (verse_end or verse_start) + 1))

    verses = []
    source_chapter = (latin.get("chapters") or {}).get(str(chapter)) or {}
    for number in numbers:
        if str(number) not in dra_chapter:
            raise HTTPException(status_code=404, detail="logos_douay_verse_not_found")

        if alignment.get("exact") is True:
            text = source_chapter.get(str(number))
            if text is None:
                raise HTTPException(status_code=404, detail="logos_vulgate_verse_not_found")
            source_rows = [{"chapter": chapter, "verse": number, "surface": text}]
            relationship = "identity"
            mapping_segment = None
            mapping_version = None
        else:
            mapped = canonical_source_mapping(book_id, "latin", chapter, number)
            if mapped is None:
                raise RuntimeError(f"Verified Vulgate chapter lacks canonical mapping for {book_id} {chapter}:{number}")
            source_rows = _source_rows(latin, list(mapped.get("source_refs") or []))
            if not source_rows:
                raise RuntimeError(f"Verified Vulgate map produced no source text for {book_id} {chapter}:{number}")
            relationship = str(mapped.get("relationship") or "")
            mapping_segment = mapped.get("segment_id")
            mapping_version = mapped.get("mapping_version")

        verses.append({
            "verse": number,
            "surface": " ".join(row["surface"] for row in source_rows),
            "source_verses": source_rows,
            "mapping_relationship": relationship,
            "mapping_segment": mapping_segment,
            "mapping_version": mapping_version,
        })

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
        "note": "The Latin surface is served locally from the pinned public-domain Clementine corpus. Verified versification maps preserve each source verse boundary in source_verses; the display surface only concatenates mapped source records for the canonical row. No Latin lemma, morphology, gloss or transliteration is fabricated.",
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
