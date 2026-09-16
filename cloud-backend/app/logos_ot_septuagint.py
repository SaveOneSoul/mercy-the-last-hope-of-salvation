import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _corpus_book, _corpus_manifest, _parse_corpus_reference


router = APIRouter(prefix="/ot-septuagint", tags=["Logos Septuagint Old Testament"])
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "grc_ot_swete_protocanonical"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
BOOKS_DIR = CORPUS_DIR / "sharealike" / "first1kgreek_swete_cc-by-sa-4.0" / "books"
EXPECTED_SOURCE_COMMIT = "8ee111eb44ecef4120c844e10749178d95d1f30c"
EXPECTED_BOOK_COUNT = 37


@lru_cache(maxsize=1)
def _ot_septuagint_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("corpus_id") != "grc_ot_swete_protocanonical":
        raise RuntimeError("Unexpected Logos OT Septuagint corpus id")
    if manifest.get("production_enabled") is not True:
        raise RuntimeError("Logos OT Septuagint corpus is not production-enabled")
    if int(manifest.get("book_count") or 0) != EXPECTED_BOOK_COUNT:
        raise RuntimeError("Logos OT Septuagint book count changed")
    source = manifest.get("source") or {}
    if source.get("commit") != EXPECTED_SOURCE_COMMIT or source.get("license") != "CC BY-SA 4.0":
        raise RuntimeError("Logos OT Septuagint source lock changed")
    if source.get("share_alike") is not True or source.get("isolation_required") is not True:
        raise RuntimeError("Logos OT Septuagint ShareAlike boundary changed")
    vers = manifest.get("versification") or {}
    if vers.get("runtime_exact_identity_required") is not True or vers.get("automatic_remapping") is not False:
        raise RuntimeError("Logos OT Septuagint versification contract changed")
    return manifest


@lru_cache(maxsize=64)
def _septuagint_book(book_id: str) -> dict:
    safe = "".join(ch for ch in str(book_id).upper() if ch.isalnum())
    if safe != str(book_id).upper():
        raise RuntimeError("Invalid Septuagint book id")
    path = BOOKS_DIR / f"{safe}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="logos_ot_septuagint_reference_not_in_protocanonical_scope")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("book_id") != safe or payload.get("production_enabled") is not True:
        raise RuntimeError("OT Septuagint packaged book identity changed")
    source = payload.get("source") or {}
    if source.get("license") != "CC BY-SA 4.0" or source.get("share_alike") is not True:
        raise RuntimeError("OT Septuagint packaged book rights changed")
    return payload


def _require_installed() -> dict:
    manifest = _ot_septuagint_manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="logos_ot_septuagint_corpus_not_installed")
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
    result: set[int] = set()
    for key in chapter:
        if not str(key).isdigit():
            return None
        result.add(int(str(key)))
    return result


def _chapter_identity(book_id: str, chapter: int, greek: dict) -> dict:
    source_chapter = (greek.get("chapters") or {}).get(str(chapter))
    if not source_chapter:
        return {"exact": False, "reason": "septuagint_chapter_missing", "source_verse_count": 0, "dra_verse_count": 0}
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
        "reason": "exact_chapter_verse_identity" if exact else "septuagint_dra_verse_identity_differs",
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
    if str(book_meta.get("testament")) != "OT":
        raise HTTPException(status_code=404, detail="logos_ot_septuagint_ot_reference_required")
    book_id = str(book_meta.get("id"))
    supported = set(manifest.get("supported_canonical_books") or [])
    if book_id not in supported:
        raise HTTPException(status_code=404, detail="logos_ot_septuagint_reference_not_in_protocanonical_scope")

    greek = _septuagint_book(book_id)
    identity = _chapter_identity(book_id, chapter, greek)
    if identity.get("exact") is not True:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "logos_ot_septuagint_versification_mapping_required",
                "reference": _canonical_reference(str(book_meta.get("name")), chapter, verse_start, verse_end),
                "alignment": identity,
                "message": "This Swete Septuagint chapter is not served against Douay-Rheims until an explicit versification mapping is validated.",
            },
        )

    source_chapter = (greek.get("chapters") or {}).get(str(chapter)) or {}
    if verse_start is None:
        selected = sorted(int(v) for v in source_chapter if str(v).isdigit())
    else:
        selected = list(range(verse_start, (verse_end or verse_start) + 1))
    verses = []
    for number in selected:
        row = source_chapter.get(str(number))
        if row is None:
            raise HTTPException(status_code=404, detail="logos_ot_septuagint_source_verse_not_found")
        verses.append({
            "verse": number,
            "source_reference": row.get("source_reference"),
            "source_chapter": row.get("source_chapter"),
            "source_verse": row.get("source_verse"),
            "surface": row.get("surface"),
        })

    source = greek.get("source") or {}
    return {
        "reference": _canonical_reference(str(book_meta.get("name")), chapter, verse_start, verse_end),
        "book": str(book_meta.get("name")),
        "book_id": book_id,
        "chapter": chapter,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "language": "grc",
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "primary_witness": {
            "witness_id": greek.get("witness_id"),
            "name": greek.get("book"),
            "witness_role": greek.get("witness_role"),
            "license": source.get("license"),
            "share_alike": source.get("share_alike"),
            "isolation_required": source.get("isolation_required"),
            "source": source,
            "mapping": {
                **(greek.get("mapping") or {}),
                **identity,
                "mode": "exact-dra-septuagint-chapter-verse-identity",
                "exact_verse_alignment": True,
            },
            "verses": verses,
        },
        "derived_layers": manifest.get("derived_layers") or {},
        "note": (
            "Swete Greek source boundaries are preserved under CC BY-SA 4.0. No gloss, lemma, morphology or transliteration is fabricated. "
            "Douay-Rheims alignment is exposed only for chapters whose numeric verse identities match exactly."
        ),
    }


@router.get("/catalog")
def logos_ot_septuagint_catalog(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _ot_septuagint_manifest()
    return {
        "installed": bool(manifest),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "language": manifest.get("language"),
        "scope": manifest.get("scope"),
        "book_count": manifest.get("book_count", 0),
        "chapter_count": manifest.get("chapter_count", 0),
        "verse_count": manifest.get("verse_count", 0),
        "supported_canonical_books": manifest.get("supported_canonical_books") or [],
        "production_enabled": manifest.get("production_enabled", False),
    }


@router.get("/source-rights")
def logos_ot_septuagint_source_rights(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _require_installed()
    return {
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "source": manifest.get("source") or {},
        "partition": manifest.get("partition") or {},
        "derived_layers": manifest.get("derived_layers") or {},
        "versification": manifest.get("versification") or {},
        "catholic_scope": manifest.get("catholic_scope") or {},
        "serving_contract": manifest.get("serving_contract") or {},
    }


@router.get("/interlinear")
def logos_ot_septuagint_interlinear(
    reference: str = Query(min_length=2, max_length=120),
    response: Response = None,
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    return _study_payload(reference)
