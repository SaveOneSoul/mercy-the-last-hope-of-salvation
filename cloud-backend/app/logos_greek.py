import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _corpus_book, _corpus_manifest, _parse_corpus_reference
from .logos_versification import canonical_source_mapping, mapping_status


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


def _dra_book_meta(book_id: str) -> dict:
    for row in _corpus_manifest().get("books") or []:
        if str(row.get("id")) == book_id:
            return row
    raise HTTPException(status_code=404, detail="logos_book_not_in_catholic_canon")


def _dra_chapter(book_id: str, chapter: int) -> dict:
    meta = _dra_book_meta(book_id)
    payload = _corpus_book(str(meta.get("filename")))
    return (payload.get("chapters") or {}).get(str(chapter)) or {}


def _numeric_keys(chapter: dict) -> set[int] | None:
    out: set[int] = set()
    for key in chapter:
        text = str(key)
        if not text.isdigit():
            return None
        out.add(int(text))
    return out


def _chapter_versification(book_id: str, chapter: int, surface_chapter: dict) -> dict:
    dra_chapter = _dra_chapter(book_id, chapter)
    source_set = _numeric_keys(surface_chapter)
    dra_set = _numeric_keys(dra_chapter)
    numeric_identity = bool(
        surface_chapter
        and dra_chapter
        and source_set is not None
        and dra_set is not None
        and source_set == dra_set
    )
    registry = mapping_status(book_id, "greek", chapter)
    verified_map = bool(registry and registry.get("status") == "verified-map")
    exact = numeric_identity and not verified_map
    return {
        "exact": exact,
        "numeric_identifier_identity": numeric_identity,
        "verified_mapping": verified_map,
        "mode": (
            "verified-explicit-map"
            if verified_map
            else "exact-dra-sblgnt-chapter-verse-identity"
            if exact
            else "explicit-mapping-required"
        ),
        "source_verse_count": len(surface_chapter),
        "dra_verse_count": len(dra_chapter),
        "automatic_remapping": False,
        "mapping": registry if verified_map else None,
    }


def _canonical_numbers(dra_chapter: dict, verse_start: int | None, verse_end: int | None) -> list[int]:
    available = {int(key) for key in dra_chapter if str(key).isdigit()}
    if verse_start is None:
        return sorted(available)
    selected: list[int] = []
    for number in range(verse_start, (verse_end or verse_start) + 1):
        if number not in available:
            raise HTTPException(status_code=404, detail="logos_douay_verse_not_found")
        selected.append(number)
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
    dra_chapter = _dra_chapter(book_id, chapter_number)
    if not dra_chapter:
        raise HTTPException(status_code=404, detail="logos_douay_chapter_not_found")

    versification = _chapter_versification(book_id, chapter_number, surface_chapter)
    canonical_ref = _canonical_reference(book_name, chapter_number, verse_start, verse_end)
    if versification.get("exact") is not True and versification.get("verified_mapping") is not True:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "logos_greek_nt_versification_mapping_required",
                "reference": canonical_ref,
                "versification": versification,
                "message": "The pinned SBLGNT witness is installed, but this chapter is not rendered against Douay-Rheims until an explicit versification mapping is verified.",
            },
        )

    surface_verses = []
    linguistic_verses = []
    alignment_verses = []
    compatibility_tokens = []
    compatibility_token_ids: set[str] = set()

    if versification.get("exact") is True:
        verse_ids = _selected_verse_ids(surface_chapter, verse_start, verse_end)
        work = [
            {
                "canonical_verse": int(verse_id),
                "relationship": "identity",
                "segment_id": None,
                "mapping_version": None,
                "source_refs": [{"chapter": str(chapter_number), "verse": str(verse_id)}],
            }
            for verse_id in verse_ids
        ]
    else:
        work = []
        for number in _canonical_numbers(dra_chapter, verse_start, verse_end):
            mapped = canonical_source_mapping(book_id, "greek", chapter_number, number)
            if mapped is None:
                raise RuntimeError(
                    f"Verified Greek NT chapter lacks canonical mapping for {book_id} {chapter_number}:{number}"
                )
            work.append(
                {
                    "canonical_verse": number,
                    "relationship": str(mapped.get("relationship") or ""),
                    "segment_id": mapped.get("segment_id"),
                    "mapping_version": mapped.get("mapping_version"),
                    "source_refs": list(mapped.get("source_refs") or []),
                }
            )

    surface_chapters = surface.get("chapters") or {}
    linguistic_chapters = linguistics.get("chapters") or {}
    for item in work:
        canonical_verse = int(item["canonical_verse"])
        source_refs = item["source_refs"]
        relationship = item["relationship"]
        source_surface_rows = []
        source_linguistic_rows = []
        source_alignment_rows = []

        for ref in source_refs:
            source_chapter_number = int(str(ref.get("chapter")))
            source_verse_id = str(ref.get("verse"))
            source_surface = (surface_chapters.get(str(source_chapter_number)) or {}).get(source_verse_id)
            if source_surface is None:
                raise RuntimeError(
                    f"Verified Greek NT mapping references missing SBLGNT verse {source_chapter_number}:{source_verse_id}"
                )
            source_linguistic = (linguistic_chapters.get(str(source_chapter_number)) or {}).get(source_verse_id) or {
                "annotation_status": "unavailable-in-pinned-morphgnt",
                "tokens": [],
            }
            source_align = align_index.get((source_chapter_number, source_verse_id))
            if not source_align:
                raise RuntimeError(
                    f"Verified Greek NT mapping references missing alignment row {source_chapter_number}:{source_verse_id}"
                )
            source_surface_rows.append(
                {
                    "chapter": source_chapter_number,
                    "verse": source_verse_id,
                    "text": source_surface.get("text") or "",
                    "tokens": source_surface.get("tokens") or [],
                }
            )
            source_linguistic_rows.append(
                {
                    "chapter": source_chapter_number,
                    "verse": source_verse_id,
                    "annotation_status": source_linguistic.get("annotation_status") or "available",
                    "reason": source_linguistic.get("reason"),
                    "tokens": source_linguistic.get("tokens") or [],
                }
            )
            source_alignment_rows.append(source_align)

        source_missing = relationship == "canonical-only"
        if not source_refs and not source_missing:
            raise RuntimeError(
                f"Verified Greek NT mapping produced no source rows for {book_id} {chapter_number}:{canonical_verse}"
            )

        surface_tokens = [
            token
            for row in source_surface_rows
            for token in (row.get("tokens") or [])
        ]
        linguistic_tokens = [
            token
            for row in source_linguistic_rows
            for token in (row.get("tokens") or [])
        ]
        ling_by_id = {str(row.get("id")): row for row in linguistic_tokens}
        annotation_statuses = {
            str(row.get("annotation_status") or "available")
            for row in source_linguistic_rows
        }
        annotation_status = (
            "canonical-only-source-gap"
            if source_missing
            else "available"
            if not annotation_statuses or annotation_statuses == {"available"}
            else sorted(annotation_statuses)[0]
        )

        surface_verses.append(
            {
                "verse": str(canonical_verse),
                "text": " ".join(str(row.get("text") or "") for row in source_surface_rows).strip(),
                "tokens": surface_tokens,
                "source_verses": source_surface_rows,
                "source_missing": source_missing,
                "mapping_relationship": relationship,
                "mapping_segment": item["segment_id"],
                "mapping_version": item["mapping_version"],
            }
        )
        linguistic_verses.append(
            {
                "verse": str(canonical_verse),
                "annotation_status": annotation_status,
                "reason": (
                    "No Greek source verse exists for this Douay-Rheims canonical row in the pinned SBLGNT witness."
                    if source_missing
                    else next((row.get("reason") for row in source_linguistic_rows if row.get("reason")), None)
                ),
                "tokens": linguistic_tokens,
                "source_verses": source_linguistic_rows,
                "source_missing": source_missing,
                "mapping_relationship": relationship,
            }
        )
        alignment_verses.append(
            {
                "chapter": chapter_number,
                "verse": str(canonical_verse),
                "mapping_relationship": relationship,
                "source_refs": [
                    {"chapter": row["chapter"], "verse": row["verse"]}
                    for row in source_surface_rows
                ],
                "source_missing": source_missing,
                "source_alignment_rows": source_alignment_rows,
            }
        )

        for token in surface_tokens:
            token_id = str(token.get("id"))
            if token_id in compatibility_token_ids:
                continue
            compatibility_token_ids.add(token_id)
            ling_token = ling_by_id.get(token_id) or {}
            compatibility_tokens.append(
                {
                    "id": token_id,
                    "verse": str(canonical_verse),
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
    note = (
        "SBLGNT surface text and MorphGNT linguistic annotations are served as separate license partitions. "
        "John 7:53–8:11 preserves the SBLGNT surface while morphology remains explicitly unavailable in the pinned MorphGNT source."
    )
    if versification.get("verified_mapping") is True:
        note += (
            " A verified versification map aligns Douay-Rheims canonical rows to intact pinned SBLGNT source records. "
            "Canonical-only rows remain empty and do not synthesize Greek text, transliteration, lemma, POS, or morphology."
        )
    return {
        "reference": canonical_ref,
        "book": book_name,
        "book_id": book_id,
        "chapter": chapter_number,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "language": "grc",
        "label": "Greek New Testament — SBLGNT + MorphGNT",
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "versification": versification,
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
        "note": note,
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
