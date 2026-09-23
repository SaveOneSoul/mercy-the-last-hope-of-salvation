from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _parse_corpus_reference, _passage, _passage_payload
from .logos_ot_greek import _ot_greek_manifest, _study_payload as _accepted_greek_payload
from .logos_ot_greek_full import _manifest as _full_greek_manifest, _study_payload as _full_greek_payload
from .logos_ot_latin import _manifest as _latin_manifest, _study_payload as _latin_payload
from .logos_ot_semitic import _ot_semitic_manifest, _study_payload as _semitic_payload
from .logos_versification import mapping_status, registry_summary

router = APIRouter(prefix="/ot-interlinear", tags=["Logos Unified Old Testament Interlinear"])


def _lane(callable_, reference: str) -> dict:
    try:
        return {"status": "available", "data": callable_(reference)}
    except HTTPException as exc:
        if exc.status_code == 404:
            return {"status": "not-applicable", "detail": exc.detail}
        if exc.status_code == 409:
            return {"status": "mapping-required", "detail": exc.detail}
        raise


def _greek_lane(reference: str) -> dict:
    accepted = _lane(_accepted_greek_payload, reference)
    if accepted["status"] == "available":
        accepted["source_scope"] = "accepted-catholic-deuterocanonical-and-additions"
        return accepted
    if accepted["status"] == "mapping-required":
        return accepted
    try:
        full = _lane(_full_greek_payload, reference)
    except RuntimeError as exc:
        if str(exc) != "Ambiguous verified range mapping requires a lane-specific resolver":
            raise
        return {
            "status": "mapping-required",
            "detail": {
                "code": "logos_full_lxx_verse_mapping_required",
                "reference": reference,
                "message": "The Greek source is installed, but this chapter has a verified structural range whose individual source verses cannot be aligned to Douay verses. Select the Greek witness by its native divisions when available; no verse equivalence is inferred.",
            },
        }
    if full["status"] == "available":
        full["source_scope"] = "complete-protocanonical-greek-ot"
    return full


def _english_lane(reference: str) -> dict:
    payload = _passage_payload(_passage(reference))
    english = ((payload.get("languages") or {}).get("en") or {})
    return {
        "status": "available",
        "data": {
            "reference": payload.get("reference"),
            "book": payload.get("book"),
            "chapter": payload.get("chapter"),
            "verse_start": payload.get("verse_start"),
            "verse_end": payload.get("verse_end"),
            "language": "en",
            "label": english.get("label") or "English — Douay-Rheims 1899",
            "text": english.get("text") or "",
            "verses": payload.get("verses") or [],
            "source": english.get("source") or {},
            "note": english.get("note"),
        },
    }


@router.get("/catalog")
def catalog(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    semitic = _ot_semitic_manifest()
    accepted_greek = _ot_greek_manifest()
    full_greek = _full_greek_manifest()
    latin = _latin_manifest()
    return {
        "module": "Logos Unified Catholic Old Testament Interlinear",
        "production_enabled": bool(semitic and accepted_greek and full_greek and latin),
        "catholic_ot_book_count": 46,
        "lanes": {
            "english": {"installed": True, "label": "Douay-Rheims 1899", "language": "en"},
            "semitic": {
                "installed": bool(semitic),
                "corpus_id": semitic.get("corpus_id"),
                "languages": semitic.get("languages") or ["he", "arc"],
                "book_scope": 39,
            },
            "greek": {
                "installed": bool(accepted_greek and full_greek),
                "protocanonical_corpus_id": full_greek.get("corpus_id"),
                "protocanonical_book_scope": full_greek.get("book_count", 0),
                "first1k_swete_book_scope": full_greek.get("first1k_swete_book_scope_count", 0),
                "ecclesiastes_fallback_book_scope": full_greek.get("ecclesiastes_fallback_book_scope_count", 0),
                "deuterocanonical_corpus_id": accepted_greek.get("corpus_id"),
                "accepted_witness_count": ((accepted_greek.get("phase1b_acceptance") or {}).get("witness_count", 0)),
                "language": "grc",
            },
            "latin": {
                "installed": bool(latin),
                "corpus_id": latin.get("corpus_id"),
                "book_count": latin.get("book_count", 0),
                "language": "la",
            },
        },
        "versification_registry": registry_summary(),
        "alignment_policy": {
            "english_primary": True,
            "source_boundaries_preserved": True,
            "automatic_versification_remapping": False,
            "parallel_render_requires_verified_mapping": True,
            "verified_registry_maps_are_applied_only_by_explicit_lane_adapters": True,
            "unavailable_linguistic_layers_are_never_fabricated": True,
        },
    }


@router.get("")
def interlinear(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    book_meta, chapter, _, _ = _parse_corpus_reference(reference)
    if str(book_meta.get("testament")) != "OT":
        raise HTTPException(status_code=404, detail="logos_unified_interlinear_ot_reference_required")

    english = _english_lane(reference)
    canonical_reference = str((english.get("data") or {}).get("reference") or reference)
    semitic = _lane(_semitic_payload, canonical_reference)
    greek = _greek_lane(canonical_reference)
    latin = _lane(_latin_payload, canonical_reference)
    book_id = str(book_meta.get("id"))
    return {
        "reference": canonical_reference,
        "book": book_meta.get("name"),
        "book_id": book_id,
        "testament": "OT",
        "lanes": {
            "english": english,
            "semitic": semitic,
            "greek": greek,
            "latin": latin,
        },
        "versification_registry": {
            "semitic": mapping_status(book_id, "semitic", chapter),
            "greek": mapping_status(book_id, "greek", chapter),
            "latin": mapping_status(book_id, "latin", chapter),
        },
        "alignment_policy": {
            "english_primary": True,
            "source_boundaries_preserved": True,
            "automatic_versification_remapping": False,
            "mapping_required_is_exposed_not_hidden": True,
            "verified_registry_maps_are_applied_only_by_explicit_lane_adapters": True,
        },
        "note": "This response unifies deterministic local Catholic OT source layers. A lane marked mapping-required remains blocked until an explicit, evidence-backed source/Douay mapping is both registry-verified and enabled by that lane's runtime adapter.",
    }
