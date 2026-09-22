import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

router = APIRouter(
    prefix="/nt-tagnt-linguistics",
    tags=["Logos Greek NT Supplemental Linguistics"],
)
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "grc_nt_tagnt_john_pa"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
CORPUS_ID = "grc_nt_tagnt_john_pa"
SOURCE_COMMIT = "ae39711d7843b2902d54993e432de9c12d6a4b9a"
SOURCE_BLOB = "705c1bc1cf752e013efcef99b8d9a3b7853bf843"


@lru_cache(maxsize=1)
def _manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if payload.get("corpus_id") != CORPUS_ID:
        raise RuntimeError("Unexpected TAGNT John supplement corpus id")
    if payload.get("production_enabled") is not True or payload.get("status") != "production-installed":
        raise RuntimeError("TAGNT John supplement is not production-enabled")
    source = payload.get("source") or {}
    if source.get("commit") != SOURCE_COMMIT or source.get("git_blob_sha1") != SOURCE_BLOB:
        raise RuntimeError("TAGNT John immutable source pin changed")
    if source.get("license") != "CC BY 4.0":
        raise RuntimeError("TAGNT John source license changed")
    policy = payload.get("witness_policy") or {}
    if policy.get("automatic_attachment_to_sblgnt") is not False:
        raise RuntimeError("TAGNT John may not auto-attach to SBLGNT")
    if policy.get("tagnt_is_amalgamated") is not True:
        raise RuntimeError("TAGNT John amalgamated-witness disclosure is missing")
    return payload


@router.get("/catalog")
def catalog(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _manifest()
    return {
        "installed": bool(manifest),
        "production_enabled": manifest.get("production_enabled", False),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "book": manifest.get("book"),
        "verse_count": manifest.get("verse_count", 0),
        "token_count": manifest.get("token_count", 0),
        "scope": manifest.get("scope"),
        "source": manifest.get("source") or {},
        "witness_policy": manifest.get("witness_policy") or {},
        "note": manifest.get("note"),
    }


@router.get("/verse")
def verse(
    reference: str = Query(min_length=4, max_length=12),
    response: Response = None,
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    normalized = reference.strip()
    if normalized.lower().startswith("john "):
        normalized = normalized[5:].strip()
    manifest = _manifest()
    row = next((item for item in (manifest.get("verses") or []) if str(item.get("reference")) == normalized), None)
    if row is None:
        raise HTTPException(status_code=404, detail="logos_tagnt_john_supplement_verse_not_found")
    return {
        "book": "John",
        "reference": row.get("canonical_reference"),
        "language": "grc",
        "linguistic_source": "STEPBible TAGNT",
        "relationship_to_primary_surface": "supplemental-parallel-linguistic-witness",
        "tokens": row.get("tokens") or [],
        "source": manifest.get("source") or {},
        "note": (
            "TAGNT supplies linguistic evidence for the passage absent from the pinned MorphGNT annotation layer. "
            "The token rows preserve TAGNT's edition membership and variants and are not represented as MorphGNT or token-identical SBLGNT annotations."
        ),
    }
