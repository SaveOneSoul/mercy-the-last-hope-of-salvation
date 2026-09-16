import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _parse_corpus_reference


router = APIRouter(prefix="/greek", tags=["Logos Greek New Testament"])
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "grc_sblgnt_morphgnt"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
PHASE1_DIR = CORPUS_DIR / "phase1"


@lru_cache(maxsize=1)
def _greek_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("corpus_id") != "grc_sblgnt_morphgnt":
        raise RuntimeError("Unexpected Logos Greek NT corpus id")
    if manifest.get("production_enabled") is not True:
        raise RuntimeError("Logos Greek NT corpus is not production-enabled")
    accepted = manifest.get("phase1_acceptance") or {}
    if int(accepted.get("book_count") or 0) != 27:
        raise RuntimeError("Logos Greek NT corpus does not contain 27 books")
    return manifest


@lru_cache(maxsize=96)
def _layer_book(layer: str, book_id: str) -> dict:
    if layer not in {"surface", "linguistics", "alignment"}:
        raise RuntimeError("Invalid Logos Greek NT layer")
    safe_id = "".join(ch for ch in str(book_id).upper() if ch.isalnum())
    if safe_id != str(book_id).upper():
        raise RuntimeError("Invalid Logos Greek NT book id")
    path = PHASE1_DIR / layer / f"{safe_id}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="logos_greek_book_not_installed")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _require_installed() -> dict:
    manifest = _greek_manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="logos_greek_nt_corpus_not_installed")
    return manifest


def _canonical_reference(book: str, chapter: int, verse_start: int | None, verse_end: int | None) -> str:
    if verse_start is None:
        return f"{book} {chapter}"
    if verse_end is not None and verse_end != verse_start:
        return f"{book} {chapter}:{verse_start}-{verse_end}"
    return f"{book} {chapter}:{verse_start}"


def _selected_verse_ids(chapter: dict, verse_start: int | None, verse_end: int | None) -> list[str]:
    available = {int(key): str(key) for key in chapter if str(key).isdigit()}
    if verse_start is None:
        return [available[number] for number in sorted(available)]
    selected = []
    for number in range(verse_start, (verse_end or verse_start) + 1):
        verse_id = available.get(number)
        if verse_id is None:
            raise HTTPException(status_code=404, detail="logos_greek_verse_not_found")
        selected.append(verse_id)
    return selected


def _alignment_index(payload: dict) -> dict[tuple[int, str], dict]:
    return {
        (int(row.get("chapter")), str(row.get("verse"))): row
        for row in (payload.get("verses") or [])
    }


def _interlinear_payload(reference: str) -> dict:
    manifest = _require_installed()
    book_meta, chapter_number, verse_start, verse_end = _parse_corpus_reference(reference)
    if str(book_meta.get("testament")) != "NT":
        raise HTTPException(status_code=404, detail="logos_greek_nt_reference_required")

    book_id = str(book_meta.get("id"))
    book_name = str(book_meta.get("name"))
    surface = _layer_book("surface", book_id)
    linguistics = _layer_book("linguistics", book_id)
    alignment = _layer_book("alignment", book_id)

    surface_chapter = (surface.get("chapters") or {}).get(str(chapter_number))
    if not surface_chapter:
        raise HTTPException(status_code=404, detail="logos_greek_chapter_not_found")
    linguistic_chapter = (linguistics.get("chapters") or {}).get(str(chapter_number)) or {}
    align_index = _alignment_index(alignment)
    verse_ids = _selected_verse_ids(surface_chapter, verse_start, verse_end)

    surface_verses = []
    linguistic_verses = []
    alignment_verses = []
    compatibility_tokens = []

    for verse_id in verse_ids:
        surface_row = surface_chapter[verse_id]
        ling_row = linguistic_chapter.get(verse_id) or {
            "annotation_status": "unavailable-in-pinned-morphgnt",
            "tokens": [],
        }
        align_row = align_index.get((chapter_number, verse_id))
        if not align_row:
            raise HTTPException(status_code=500, detail="logos_greek_alignment_missing")

        surface_tokens = surface_row.get("tokens") or []
        linguistic_tokens = ling_row.get("tokens") or []
        ling_by_id = {str(row.get("id")): row for row in linguistic_tokens}
        annotation_status = ling_row.get("annotation_status") or "available"

        surface_verses.append(
            {
                "verse": verse_id,
                "text": surface_row.get("text") or "",
                "tokens": surface_tokens,
            }
        )
        linguistic_verses.append(
            {
                "verse": verse_id,
                "annotation_status": annotation_status,
                "reason": ling_row.get("reason"),
                "tokens": linguistic_tokens,
            }
        )
        alignment_verses.append(align_row)

        for token in surface_tokens:
            token_id = str(token.get("id"))
            ling_token = ling_by_id.get(token_id) or {}
            compatibility_tokens.append(
                {
                    "id": token_id,
                    "verse": verse_id,
                    "position": token.get("position"),
                    "surface": token.get("surface"),
                    "transliteration": token.get("transliteration"),
                    "lemma": ling_token.get("lemma"),
                    "part_of_speech_code": ling_token.get("part_of_speech_code"),
                    "morphology": ling_token.get("morphology"),
                    "normalized": ling_token.get("normalized"),
                    "annotation_status": annotation_status,
                    "gloss": None,
                }
            )

    partitions = manifest.get("partitions") or {}
    sources = manifest.get("sources") or {}
    return {
        "reference": _canonical_reference(book_name, chapter_number, verse_start, verse_end),
        "book": book_name,
        "book_id": book_id,
        "chapter": chapter_number,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "language": "grc",
        "label": "Greek New Testament — SBLGNT + MorphGNT",
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "surface": {
            "source": sources.get("surface") or {},
            "license_partition": partitions.get("surface") or {},
            "verses": surface_verses,
        },
        "linguistics": {
            "source": sources.get("linguistics") or {},
            "license_partition": partitions.get("linguistics") or {},
            "verses": linguistic_verses,
        },
        "alignment": {
            "license_partition": partitions.get("alignment") or {},
            "verses": alignment_verses,
        },
        "tokens": compatibility_tokens,
        "gloss_layer": manifest.get("gloss_layer") or {},
        "annotation_gap_policy": manifest.get("annotation_gap_policy") or {},
        "note": (
            "SBLGNT surface text and MorphGNT linguistic annotations are served as separate license partitions. "
            "John 7:53–8:11 preserves the SBLGNT surface while morphology remains explicitly unavailable in the pinned MorphGNT source."
        ),
    }


@router.get("/catalog")
def logos_greek_catalog(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _greek_manifest()
    accepted = manifest.get("phase1_acceptance") or {}
    return {
        "installed": bool(manifest),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "language": manifest.get("language"),
        "scope": manifest.get("scope"),
        "book_count": accepted.get("book_count", 0),
        "chapter_count": accepted.get("chapter_count", 0),
        "verse_count": accepted.get("verse_count", 0),
        "surface_token_count": accepted.get("surface_token_count", 0),
        "morphology_coverage_verse_count": accepted.get("morphology_coverage_verse_count", 0),
        "annotation_gap_verse_count": accepted.get("annotation_gap_verse_count", 0),
        "production_enabled": manifest.get("production_enabled", False),
    }


@router.get("/source-rights")
def logos_greek_source_rights(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _require_installed()
    return {
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "sources": manifest.get("sources") or {},
        "partitions": manifest.get("partitions") or {},
        "gloss_layer": manifest.get("gloss_layer") or {},
        "annotation_gap_policy": manifest.get("annotation_gap_policy") or {},
        "serving_contract": manifest.get("serving_contract") or {},
    }


@router.get("/interlinear")
def logos_greek_interlinear(
    reference: str = Query(min_length=2, max_length=120),
    response: Response = None,
):
    if response is not None:
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return _interlinear_payload(reference)
