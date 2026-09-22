import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

router = APIRouter(
    prefix="/ot-lxx-linguistics",
    tags=["Logos Greek OT Word-Level Linguistics"],
)

CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "grc_ot_rahlfs_lxx_morph"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
BOOK_DIR = CORPUS_DIR / "books"
CORPUS_ID = "grc_ot_rahlfs_lxx_morph"
SOURCE_COMMIT = "c91f6b1e8fb3ba37df701e6ae31f675ace71a2b2"
ARCHIVE_SHA256 = "b3c4861f47152ea8fab7d3ed78d807a9a0c2b35d07f2cb64fa9deefd6ac960a9"


@lru_cache(maxsize=1)
def _manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if payload.get("corpus_id") != CORPUS_ID:
        raise RuntimeError("Unexpected Greek OT linguistic corpus id")
    if payload.get("status") != "production-installed" or payload.get("production_enabled") is not True:
        raise RuntimeError("Greek OT linguistic corpus is not production-enabled")
    if int(payload.get("book_count") or 0) != 46:
        raise RuntimeError("Greek OT linguistic corpus does not contain 46 Catholic OT books")
    source = payload.get("source") or {}
    if source.get("commit") != SOURCE_COMMIT or source.get("archive_sha256") != ARCHIVE_SHA256:
        raise RuntimeError("Greek OT linguistic immutable source pin changed")
    if source.get("license") != "CC BY 4.0":
        raise RuntimeError("Greek OT linguistic source license changed")
    if source.get("text_edition") != "Rahlfs Septuagint (1935)":
        raise RuntimeError("Greek OT linguistic edition identity changed")
    runtime = payload.get("runtime_contract") or {}
    if runtime.get("cross_edition_relabeling_forbidden") is not True:
        raise RuntimeError("Greek OT linguistic cross-edition safety gate changed")
    if runtime.get("automatic_attachment_to_swete") is not False:
        raise RuntimeError("Greek OT linguistic witness may not auto-attach to Swete")
    if runtime.get("no_fabricated_linguistics") is not True:
        raise RuntimeError("Greek OT linguistic no-fabrication gate changed")
    return payload


@lru_cache(maxsize=64)
def _book(book_id: str) -> dict:
    safe = "".join(ch for ch in str(book_id).upper() if ch.isalnum())
    if not safe or safe != str(book_id).upper():
        raise HTTPException(status_code=400, detail="logos_greek_ot_linguistics_invalid_book_id")
    path = BOOK_DIR / f"{safe}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="logos_greek_ot_linguistics_book_not_found")
    payload = json.loads(path.read_text(encoding="utf-8"))
    if payload.get("corpus_id") != CORPUS_ID or payload.get("book_id") != safe:
        raise RuntimeError("Unexpected Greek OT linguistic book payload")
    if payload.get("production_enabled") is not True or payload.get("status") != "production-installed":
        raise RuntimeError("Greek OT linguistic book is not production-enabled")
    if payload.get("text_edition") != "Rahlfs Septuagint (1935)":
        raise RuntimeError("Greek OT linguistic book edition identity changed")
    policy = payload.get("cross_edition_policy") or {}
    if policy.get("relationship") != "separate-witness":
        raise RuntimeError("Greek OT linguistic book lost separate-witness identity")
    if policy.get("automatic_attachment_to_installed_surface") is not False:
        raise RuntimeError("Greek OT linguistic book may not auto-attach to installed Swete surface")
    return payload


def _public_token(token: dict) -> dict:
    return {
        "position": token.get("position"),
        "surface": token.get("surface"),
        "lemma": token.get("lemma"),
        "part_of_speech": token.get("part_of_speech"),
        "morphology": token.get("morphology"),
        "confidence": token.get("confidence"),
        "provenance_source": token.get("provenance_source"),
        "reasoning": token.get("reasoning"),
    }


def _public_verse(row: dict) -> dict:
    return {
        "component": row.get("component"),
        "source_ref": row.get("source_ref"),
        "tokens": [_public_token(token) for token in (row.get("tokens") or [])],
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
        "token_count": manifest.get("token_count", 0),
        "language": manifest.get("language"),
        "text_edition": (manifest.get("source") or {}).get("text_edition"),
        "source": manifest.get("source") or {},
        "quality_note": manifest.get("quality_note"),
        "cross_edition_relationship": "separate Rahlfs linguistic witness; not relabeled as Swete",
    }


@router.get("/source-rights")
def source_rights(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="logos_greek_ot_linguistics_corpus_not_installed")
    return {
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "source": manifest.get("source") or {},
        "field_provenance": manifest.get("field_provenance") or {},
        "runtime_contract": manifest.get("runtime_contract") or {},
        "quality_note": manifest.get("quality_note"),
    }


@router.get("/book")
def book(
    book_id: str = Query(min_length=2, max_length=4),
    response: Response = None,
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    payload = _book(book_id)
    return {
        "book_id": payload.get("book_id"),
        "book": payload.get("book"),
        "language": payload.get("language"),
        "text_edition": payload.get("text_edition"),
        "linguistic_source": payload.get("linguistic_source"),
        "license": payload.get("license"),
        "source_reference_system": payload.get("source_reference_system"),
        "components": payload.get("components") or [],
        "verse_count": payload.get("verse_count"),
        "token_count": payload.get("token_count"),
        "cross_edition_policy": payload.get("cross_edition_policy") or {},
    }


@router.get("/verse")
def verse(
    book_id: str = Query(min_length=2, max_length=4),
    source_ref: str = Query(min_length=3, max_length=80),
    component: str | None = Query(default=None, max_length=80),
    response: Response = None,
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    payload = _book(book_id)
    matches = [
        row
        for row in (payload.get("verses") or [])
        if str(row.get("source_ref")) == source_ref
        and (component is None or str(row.get("component")) == component)
    ]
    if not matches:
        raise HTTPException(status_code=404, detail="logos_greek_ot_linguistics_source_verse_not_found")
    if len(matches) > 1 and component is None:
        raise HTTPException(
            status_code=409,
            detail={
                "code": "logos_greek_ot_linguistics_component_required",
                "message": "This Catholic book combines multiple Rahlfs components with the same native source reference. Supply the component explicitly.",
                "components": sorted({str(row.get("component")) for row in matches}),
            },
        )
    selected = matches if len(matches) > 1 else [matches[0]]
    return {
        "book_id": payload.get("book_id"),
        "book": payload.get("book"),
        "language": "grc",
        "text_edition": payload.get("text_edition"),
        "linguistic_source": payload.get("linguistic_source"),
        "license": payload.get("license"),
        "requested_source_ref": source_ref,
        "verses": [_public_verse(row) for row in selected],
        "note": (
            "This is the source-native Rahlfs 1935/lxx-morph linguistic witness. "
            "It is intentionally separate from the installed Swete/Open Greek surface witness; "
            "no cross-edition token identity or Douay-Rheims verse identity is implied."
        ),
    }
