import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _corpus_book, _corpus_manifest, _parse_corpus_reference
from .logos_versification import canonical_source_mapping, mapping_status


router = APIRouter(prefix="/ot-semitic", tags=["Logos Hebrew/Aramaic Old Testament"])
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "heb_arc_oshb_wlc"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
PHASE1A_ROOT = CORPUS_DIR / "phase1a"
EXPECTED_ACCEPTANCE_MERGE = "c93507c2f2d7e6cec6540ac9a6f155dd6eefecc9"
EXPECTED_COUNTS = {
    "masoretic_book_witness_count": 39,
    "chapter_count": 929,
    "verse_count": 23213,
    "token_count": 305507,
    "hebrew_token_count": 300679,
    "aramaic_token_count": 4828,
    "alignment_mismatch_count": 0,
}


@lru_cache(maxsize=1)
def _ot_semitic_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("corpus_id") != "heb_arc_oshb_wlc":
        raise RuntimeError("Unexpected Logos OT Semitic corpus id")
    if manifest.get("production_enabled") is not True:
        raise RuntimeError("Logos OT Semitic corpus is not production-enabled")
    accepted = manifest.get("phase1a_acceptance") or {}
    if accepted.get("merge_commit") != EXPECTED_ACCEPTANCE_MERGE:
        raise RuntimeError("Unexpected Logos OT Phase 1A acceptance merge")
    for key, expected in EXPECTED_COUNTS.items():
        if int(accepted.get(key) or 0) != expected:
            raise RuntimeError(f"Unexpected Logos OT Semitic {key}")
    vers = manifest.get("versification") or {}
    if vers.get("runtime_exact_identity_required") is not True or vers.get("automatic_remapping") is not False:
        raise RuntimeError("Logos OT Semitic versification safety contract changed")
    return manifest


@lru_cache(maxsize=1)
def _phase1a_manifest() -> dict:
    path = PHASE1A_ROOT / "manifest.json"
    if not path.exists():
        return {}
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("production_enabled") is not False:
        raise RuntimeError("Embedded OT Phase 1A evidence must remain validation-only")
    return payload


@lru_cache(maxsize=128)
def _partition_book(partition: str, book_id: str) -> dict:
    if partition not in {"surface", "linguistics", "alignment"}:
        raise RuntimeError("Invalid OT Semitic partition")
    safe = "".join(ch for ch in str(book_id).upper() if ch.isalnum())
    if safe != str(book_id).upper():
        raise RuntimeError("Invalid OT Semitic book id")
    path = PHASE1A_ROOT / partition / f"{safe}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="logos_ot_semitic_reference_not_in_masoretic_scope")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("book_id") != safe:
        raise RuntimeError("OT Semitic packaged book identity changed")
    if payload.get("normalization_applied") is not False:
        raise RuntimeError("OT Semitic source normalization marker changed")
    return payload


def _require_installed() -> tuple[dict, dict]:
    manifest = _ot_semitic_manifest()
    phase = _phase1a_manifest()
    if not manifest or not phase:
        raise HTTPException(status_code=404, detail="logos_ot_semitic_corpus_not_installed")
    return manifest, phase


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
        text = str(key)
        if not text.isdigit():
            return None
        result.add(int(text))
    return result


def _chapter_identity(book_id: str, chapter: int, surface: dict) -> dict:
    dra_meta = _dra_book_meta(book_id)
    dra_book = _corpus_book(str(dra_meta.get("filename")))
    dra_chapter = (dra_book.get("chapters") or {}).get(str(chapter))
    if not dra_chapter:
        return {
            "exact": False,
            "verified_mapping": False,
            "reason": "dra_chapter_missing",
            "source_verse_count": 0,
            "dra_verse_count": 0,
            "automatic_remapping": False,
        }

    registry = mapping_status(book_id, "semitic", chapter)
    verified_map = bool(registry and registry.get("status") == "verified-map")
    source_chapter = ((surface.get("chapters") or {}).get(str(chapter)))
    dra_set = _numeric_verse_set(dra_chapter)

    if not source_chapter:
        if verified_map:
            return {
                "exact": False,
                "numeric_identifier_identity": False,
                "verified_mapping": True,
                "reason": "verified_explicit_cross_chapter_map",
                "mode": "verified-explicit-map",
                "source_verse_count": 0,
                "dra_verse_count": len(dra_set or set()),
                "source_verse_min": None,
                "source_verse_max": None,
                "dra_verse_min": min(dra_set) if dra_set else None,
                "dra_verse_max": max(dra_set) if dra_set else None,
                "automatic_remapping": False,
                "mapping": registry,
            }
        return {
            "exact": False,
            "verified_mapping": False,
            "reason": "source_chapter_missing_or_outside_masoretic_scope",
            "source_verse_count": 0,
            "dra_verse_count": len(dra_chapter),
            "automatic_remapping": False,
        }

    source_set = _numeric_verse_set(source_chapter)
    if source_set is None or dra_set is None:
        return {
            "exact": False,
            "verified_mapping": verified_map,
            "reason": (
                "verified_explicit_map"
                if verified_map
                else "compound_or_nonnumeric_verse_ids_require_explicit_mapping"
            ),
            "mode": "verified-explicit-map" if verified_map else "explicit-mapping-required",
            "source_verse_count": len(source_chapter),
            "dra_verse_count": len(dra_chapter),
            "automatic_remapping": False,
            "mapping": registry if verified_map else None,
        }

    numeric_identity = source_set == dra_set
    exact = numeric_identity and not verified_map
    return {
        "exact": exact,
        "numeric_identifier_identity": numeric_identity,
        "verified_mapping": verified_map,
        "reason": (
            "verified_explicit_map"
            if verified_map
            else "exact_chapter_verse_identity"
            if exact
            else "mt_dra_verse_identity_differs"
        ),
        "mode": (
            "verified-explicit-map"
            if verified_map
            else "exact-dra-source-chapter-verse-identity"
            if exact
            else "explicit-mapping-required"
        ),
        "source_verse_count": len(source_set),
        "dra_verse_count": len(dra_set),
        "source_verse_min": min(source_set) if source_set else None,
        "source_verse_max": max(source_set) if source_set else None,
        "dra_verse_min": min(dra_set) if dra_set else None,
        "dra_verse_max": max(dra_set) if dra_set else None,
        "automatic_remapping": False,
        "mapping": registry if verified_map else None,
    }


def _combined_verse(surface_row: dict, linguistic_row: dict) -> dict:
    surface_tokens = surface_row.get("tokens") or []
    linguistic_tokens = linguistic_row.get("tokens") or []
    if len(surface_tokens) != len(linguistic_tokens):
        raise RuntimeError("OT Semitic surface/linguistics token length mismatch")
    tokens = []
    for left, right in zip(surface_tokens, linguistic_tokens):
        if left.get("id") != right.get("id") or left.get("language") != right.get("language"):
            raise RuntimeError("OT Semitic token partition mismatch")
        tokens.append(
            {
                "id": left.get("id"),
                "position": left.get("position"),
                "surface": left.get("surface"),
                "language": left.get("language"),
                "lemma": right.get("lemma"),
                "morphology": right.get("morphology"),
                "source_word_id": right.get("source_word_id"),
                "source_type": right.get("source_type"),
                "source_n": right.get("source_n"),
            }
        )
    return {
        "source_osis_id": surface_row.get("source_osis_id"),
        "languages": surface_row.get("languages") or [],
        "tokens": tokens,
    }


def _mapped_source_verses(
    surface: dict,
    linguistics: dict,
    refs: list[dict],
) -> list[dict]:
    surface_chapters = surface.get("chapters") or {}
    linguistic_chapters = linguistics.get("chapters") or {}
    rows: list[dict] = []
    for ref in refs:
        source_chapter = str(ref.get("chapter"))
        source_verse = str(ref.get("verse"))
        surface_row = (surface_chapters.get(source_chapter) or {}).get(source_verse)
        linguistic_row = (linguistic_chapters.get(source_chapter) or {}).get(source_verse)
        if surface_row is None or linguistic_row is None:
            raise RuntimeError(
                f"Verified OT Semitic mapping references missing source verse {source_chapter}:{source_verse}"
            )
        combined = _combined_verse(surface_row, linguistic_row)
        rows.append(
            {
                "chapter": int(source_chapter),
                "verse": int(source_verse),
                "source_osis_id": combined.get("source_osis_id"),
                "languages": combined.get("languages") or [],
                "tokens": combined.get("tokens") or [],
            }
        )
    return rows


def _study_payload(reference: str) -> dict:
    manifest, phase = _require_installed()
    book_meta, chapter, verse_start, verse_end = _parse_corpus_reference(reference)
    if str(book_meta.get("testament")) != "OT":
        raise HTTPException(status_code=404, detail="logos_ot_semitic_ot_reference_required")

    book_id = str(book_meta.get("id"))
    supported = {str(row.get("book_id")) for row in (phase.get("books") or [])}
    if book_id not in supported:
        raise HTTPException(status_code=404, detail="logos_ot_semitic_reference_not_in_masoretic_scope")

    surface = _partition_book("surface", book_id)
    linguistics = _partition_book("linguistics", book_id)
    identity = _chapter_identity(book_id, chapter, surface)
    canonical_ref = _canonical_reference(str(book_meta.get("name")), chapter, verse_start, verse_end)
    if identity.get("exact") is not True and identity.get("verified_mapping") is not True:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "logos_ot_semitic_versification_mapping_required",
                "reference": canonical_ref,
                "alignment": identity,
                "message": "This OSHB/WLC chapter is not served against Douay-Rheims until an explicit versification mapping is validated.",
            },
        )

    dra_meta = _dra_book_meta(book_id)
    dra_book = _corpus_book(str(dra_meta.get("filename")))
    dra_chapter = (dra_book.get("chapters") or {}).get(str(chapter)) or {}
    if not dra_chapter:
        raise HTTPException(status_code=404, detail="logos_douay_chapter_not_found")

    if verse_start is None:
        selected_numbers = sorted(int(v) for v in dra_chapter if str(v).isdigit())
    else:
        selected_numbers = list(range(verse_start, (verse_end or verse_start) + 1))

    verses = []
    flat_tokens = []
    flat_token_ids: set[str] = set()
    languages: set[str] = set()

    if identity.get("exact") is True:
        source_chapter = (surface.get("chapters") or {}).get(str(chapter)) or {}
        linguistic_chapter = (linguistics.get("chapters") or {}).get(str(chapter)) or {}
        if set(source_chapter) != set(linguistic_chapter):
            raise RuntimeError("OT Semitic chapter partition verse mismatch")
        for number in selected_numbers:
            key = str(number)
            if key not in dra_chapter:
                raise HTTPException(status_code=404, detail="logos_douay_verse_not_found")
            if key not in source_chapter or key not in linguistic_chapter:
                raise HTTPException(status_code=404, detail="logos_ot_semitic_source_verse_not_found")
            combined = _combined_verse(source_chapter[key], linguistic_chapter[key])
            combined["verse"] = number
            combined["mapping_relationship"] = "identity"
            combined["mapping_segment"] = None
            combined["mapping_version"] = None
            combined["source_missing"] = False
            combined["source_verses"] = [{
                "chapter": chapter,
                "verse": number,
                "source_osis_id": combined.get("source_osis_id"),
                "languages": combined.get("languages") or [],
                "tokens": combined.get("tokens") or [],
            }]
            verses.append(combined)
            for token in combined["tokens"]:
                token_id = str(token.get("id") or "")
                if token_id not in flat_token_ids:
                    flat_token_ids.add(token_id)
                    flat_tokens.append(token)
            languages.update(str(x) for x in combined.get("languages") or [])
    else:
        for number in selected_numbers:
            if str(number) not in dra_chapter:
                raise HTTPException(status_code=404, detail="logos_douay_verse_not_found")
            mapped = canonical_source_mapping(book_id, "semitic", chapter, number)
            if mapped is None:
                raise RuntimeError(f"Verified OT Semitic chapter lacks canonical mapping for {book_id} {chapter}:{number}")
            relationship = str(mapped.get("relationship") or "")
            source_rows = _mapped_source_verses(surface, linguistics, list(mapped.get("source_refs") or []))
            source_missing = relationship == "canonical-only"
            if not source_rows and not source_missing:
                raise RuntimeError(f"Verified OT Semitic map produced no source row for {book_id} {chapter}:{number}")
            row_tokens = [
                token
                for source_row in source_rows
                for token in (source_row.get("tokens") or [])
            ]
            row_languages = sorted({
                str(language)
                for source_row in source_rows
                for language in (source_row.get("languages") or [])
            })
            row = {
                "verse": number,
                "source_osis_id": source_rows[0].get("source_osis_id") if len(source_rows) == 1 else None,
                "languages": row_languages,
                "tokens": row_tokens,
                "source_verses": source_rows,
                "source_missing": source_missing,
                "mapping_relationship": relationship,
                "mapping_segment": mapped.get("segment_id"),
                "mapping_version": mapped.get("mapping_version"),
            }
            verses.append(row)
            for token in row_tokens:
                token_id = str(token.get("id") or "")
                if token_id not in flat_token_ids:
                    flat_token_ids.add(token_id)
                    flat_tokens.append(token)
            languages.update(row_languages)

    note = (
        "Source Hebrew/Aramaic is preserved verbatim. Lemma and morphology come from the pinned OSHB annotations. "
        "No gloss or transliteration is fabricated."
    )
    if identity.get("verified_mapping") is True:
        note += (
            " A verified registry map aligns canonical rows to complete native source verse records. "
            "Split mappings may repeat one intact source verse across multiple canonical rows; source tokens are never cut or reassigned."
        )
    else:
        note += " Douay-Rheims alignment is exposed only where numeric verse identities match exactly."

    return {
        "reference": canonical_ref,
        "book": str(book_meta.get("name")),
        "book_id": book_id,
        "chapter": chapter,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "languages": sorted(languages),
        "label": "Hebrew/Aramaic Old Testament — OSHB/WLC",
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "alignment": identity,
        "verses": verses,
        "tokens": flat_tokens,
        "derived_layers": manifest.get("derived_layers") or {},
        "source": manifest.get("source") or {},
        "partitions": manifest.get("partitions") or {},
        "note": note,
    }


@router.get("/catalog")
def logos_ot_semitic_catalog(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _ot_semitic_manifest()
    accepted = manifest.get("phase1a_acceptance") or {}
    return {
        "installed": bool(manifest),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "languages": manifest.get("languages") or [],
        "scope": manifest.get("scope"),
        "book_count": accepted.get("masoretic_book_witness_count", 0),
        "chapter_count": accepted.get("chapter_count", 0),
        "verse_count": accepted.get("verse_count", 0),
        "token_count": accepted.get("token_count", 0),
        "hebrew_token_count": accepted.get("hebrew_token_count", 0),
        "aramaic_token_count": accepted.get("aramaic_token_count", 0),
        "alignment_mismatch_count": accepted.get("alignment_mismatch_count", 0),
        "production_enabled": manifest.get("production_enabled", False),
    }


@router.get("/source-rights")
def logos_ot_semitic_source_rights(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest, _ = _require_installed()
    return {
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "source": manifest.get("source") or {},
        "partitions": manifest.get("partitions") or {},
        "versification": manifest.get("versification") or {},
        "derived_layers": manifest.get("derived_layers") or {},
        "runtime_contract": manifest.get("runtime_contract") or {},
        "serving_contract": manifest.get("serving_contract") or {},
        "catholic_scope": manifest.get("catholic_scope") or {},
    }


@router.get("/interlinear")
def logos_ot_semitic_interlinear(
    reference: str = Query(min_length=2, max_length=120),
    response: Response = None,
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    return _study_payload(reference)
