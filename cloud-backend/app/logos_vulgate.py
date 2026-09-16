import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _corpus_book, _corpus_manifest, _parse_corpus_reference


router = APIRouter(prefix="/vulgate", tags=["Logos Latin Vulgate"])
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "lat_clementine_vulgate"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
BOOKS_DIR = CORPUS_DIR / "books"
EXPECTED_SOURCE_COMMIT = "38292f3f91e874d3db9e7e9bf7abd23da3217054"
EXPECTED_SOURCE_BLOB = "a9ec3099e8f641d601679242354366aff150070e"


@lru_cache(maxsize=1)
def _vulgate_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("corpus_id") != "lat_clementine_vulgate":
        raise RuntimeError("Unexpected Logos Vulgate corpus id")
    if manifest.get("production_enabled") is not True:
        raise RuntimeError("Logos Vulgate corpus is not production-enabled")
    if int(manifest.get("book_count") or 0) != 73:
        raise RuntimeError("Logos Vulgate does not contain the Catholic 73-book canon")
    source = manifest.get("source") or {}
    if source.get("commit") != EXPECTED_SOURCE_COMMIT or source.get("git_blob_sha1") != EXPECTED_SOURCE_BLOB:
        raise RuntimeError("Logos Vulgate immutable source pin changed")
    if source.get("rights") != "Public Domain":
        raise RuntimeError("Logos Vulgate source rights changed")
    vers = manifest.get("versification") or {}
    if vers.get("runtime_exact_identity_required") is not True or vers.get("automatic_remapping") is not False:
        raise RuntimeError("Logos Vulgate versification contract changed")
    return manifest


@lru_cache(maxsize=96)
def _vulgate_book(book_id: str) -> dict:
    safe = "".join(ch for ch in str(book_id).upper() if ch.isalnum())
    if safe != str(book_id).upper():
        raise RuntimeError("Invalid Vulgate book id")
    path = BOOKS_DIR / f"{safe}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="logos_vulgate_book_not_installed")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("book_id") != safe or payload.get("production_enabled") is not True:
        raise RuntimeError("Vulgate packaged book identity changed")
    return payload


def _require_installed() -> dict:
    manifest = _vulgate_manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="logos_vulgate_corpus_not_installed")
    return manifest


def _canonical_reference(book: str, chapter: int, verse_start: int | None, verse_end: int | None) -> str:
    if verse_start is None:
        return f"{book} {chapter}"
    if verse_end is not None and verse_end != verse_start:
        return f"{book} {chapter}:{verse_start}-{verse_end}"
    return f"{book} {chapter}:{verse_start}"


def _dra_book_meta(book_id: str) -> dict:
    for row in _corpus_manifest().get("books") or []:
        if str(row.get("id")) == book_id:
            return row
    raise HTTPException(status_code=404, detail="logos_book_not_in_catholic_canon")


def _numeric_verse_set(chapter: dict) -> set[int] | None:
    result = set()
    for key in chapter:
        if not str(key).isdigit():
            return None
        result.add(int(str(key)))
    return result


def _chapter_identity(book_id: str, chapter: int, latin: dict) -> dict:
    source_chapter = (latin.get("chapters") or {}).get(str(chapter))
    if not source_chapter:
        return {"exact": False, "reason": "vulgate_chapter_missing", "source_verse_count": 0, "dra_verse_count": 0}
    dra_meta = _dra_book_meta(book_id)
    dra_book = _corpus_book(str(dra_meta.get("filename")))
    dra_chapter = (dra_book.get("chapters") or {}).get(str(chapter))
    if not dra_chapter:
        return {"exact": False, "reason": "dra_chapter_missing", "source_verse_count": len(source_chapter), "dra_verse_count": 0}
    source_set = _numeric_verse_set(source_chapter)
    dra_set = _numeric_verse_set(dra_chapter)
    if source_set is None or dra_set is None:
        return {
            "exact": False,
            "reason": "compound_or_nonnumeric_verse_ids_require_explicit_mapping",
            "source_verse_count": len(source_chapter),
            "dra_verse_count": len(dra_chapter),
        }
    exact = source_set == dra_set
    return {
        "exact": exact,
        "reason": "exact_chapter_verse_identity" if exact else "vulgate_dra_verse_identity_differs",
        "source_verse_count": len(source_set),
        "dra_verse_count": len(dra_set),
        "source_verse_min": min(source_set) if source_set else None,
        "source_verse_max": max(source_set) if source_set else None,
        "dra_verse_min": min(dra_set) if dra_set else None,
        "dra_verse_max": max(dra_set) if dra_set else None,
    }


def _study_payload(reference: str) -> dict:
    manifest = _require_installed()
    book_meta, chapter, verse_start, verse_end = _parse_corpus_reference(reference)
    book_id = str(book_meta.get("id"))
    supported = set(manifest.get("supported_canonical_books") or [])
    if book_id not in supported:
        raise HTTPException(status_code=404, detail="logos_vulgate_reference_not_in_catholic_canon")
    latin = _vulgate_book(book_id)
    identity = _chapter_identity(book_id, chapter, latin)
    if identity.get("exact") is not True:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "logos_vulgate_versification_mapping_required",
                "reference": _canonical_reference(str(book_meta.get("name")), chapter, verse_start, verse_end),
                "alignment": identity,
                "message": "This Clementine Vulgate chapter is not served against Douay-Rheims until an explicit versification mapping is validated.",
            },
        )
    source_chapter = (latin.get("chapters") or {}).get(str(chapter)) or {}
    if verse_start is None:
        selected = sorted(int(v) for v in source_chapter if str(v).isdigit())
    else:
        selected = list(range(verse_start, (verse_end or verse_start) + 1))
    verses = []
    for number in selected:
        text = source_chapter.get(str(number))
        if text is None:
            raise HTTPException(status_code=404, detail="logos_vulgate_source_verse_not_found")
        verses.append({
            "verse": number,
            "source_reference": f"{latin.get('book') or book_meta.get('name')} {chapter}:{number}",
            "surface": text,
        })
    return {
        "reference": _canonical_reference(str(book_meta.get("name")), chapter, verse_start, verse_end),
        "book": str(book_meta.get("name")),
        "book_id": book_id,
        "chapter": chapter,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "language": "la",
        "label": "Latin — Clementine Vulgate",
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "alignment": {
            **identity,
            "mode": "exact-dra-vulgate-chapter-verse-identity",
            "automatic_remapping": False,
        },
        "verses": verses,
        "source": manifest.get("source") or {},
        "derived_layers": manifest.get("derived_layers") or {},
        "note": "Public-domain Clementine Latin is served only where chapter/verse identities match the installed Douay-Rheims corpus exactly. No Latin linguistic annotation is fabricated.",
    }


@router.get("/catalog")
def logos_vulgate_catalog(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _vulgate_manifest()
    return {
        "installed": bool(manifest),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "language": manifest.get("language"),
        "scope": manifest.get("scope"),
        "book_count": manifest.get("book_count", 0),
        "chapter_count": manifest.get("chapter_count", 0),
        "verse_count": manifest.get("verse_count", 0),
        "production_enabled": manifest.get("production_enabled", False),
    }


@router.get("/source-rights")
def logos_vulgate_source_rights(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _require_installed()
    return {
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "source": manifest.get("source") or {},
        "derived_layers": manifest.get("derived_layers") or {},
        "versification": manifest.get("versification") or {},
        "serving_contract": manifest.get("serving_contract") or {},
    }


@router.get("/interlinear")
def logos_vulgate_interlinear(
    reference: str = Query(min_length=2, max_length=120),
    response: Response = None,
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    return _study_payload(reference)
