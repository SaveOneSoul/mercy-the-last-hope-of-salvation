import json
import re
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from .magisterium import CatholicChatIn, ask_magisterium

router = APIRouter(prefix="/api/logos", tags=["Logos"])
DATA_PATH = Path(__file__).with_name("logos_seed.json")


class LogosAIIn(BaseModel):
    reference: str = Field(min_length=2, max_length=120)
    theme: str = Field(min_length=2, max_length=80)
    question: str | None = Field(default=None, max_length=1000)
    language: str = Field(default="en", pattern="^(en|kha)$")


@lru_cache(maxsize=1)
def _data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or "unknown"
    return request.client.host if request.client else "unknown"


def _normalize_reference(value: str) -> str:
    value = re.sub(r"\s+", " ", (value or "").strip()).lower()
    value = re.sub(r"\s*:\s*", ":", value)
    return value


def _passage(reference: str) -> dict:
    key = _normalize_reference(reference)
    item = _data().get("passages", {}).get(key)
    if item is None:
        raise HTTPException(status_code=404, detail="logos_passage_not_in_local_corpus")
    return item


def _source_index() -> dict[str, dict]:
    return {str(item.get("id")): item for item in _data().get("sources", [])}


def _source_for(source_id: str | None) -> dict | None:
    if not source_id:
        return None
    return _source_index().get(source_id)


def _passage_payload(item: dict) -> dict:
    languages = {}
    for code, row in (item.get("languages") or {}).items():
        entry = dict(row)
        source = _source_for(entry.get("source_id"))
        if source:
            entry["source"] = {
                "id": source.get("id"),
                "title": source.get("title"),
                "status": source.get("status"),
                "rights": source.get("rights"),
                "allowed_display_scope": source.get("allowed_display_scope"),
            }
        languages[code] = entry
    return {
        "reference": item.get("reference"),
        "book": item.get("book"),
        "testament": item.get("testament"),
        "languages": languages,
        "available_language_codes": [code for code, row in languages.items() if row.get("text")],
        "rights_notice": _data().get("editorial_policy", {}).get("rule"),
    }


def _all_media() -> list[dict]:
    return list(_data().get("media") or [])


@router.get("/catalog")
def logos_catalog(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    data = _data()
    return {
        "module": "Logos — Biblical Study & Catholic Exegesis",
        "version": data.get("version"),
        "canon": "Catholic 73-book canon",
        "book_count": len(data.get("books") or []),
        "books": data.get("books") or [],
        "seed_references": [row.get("reference") for row in (data.get("passages") or {}).values()],
        "ai_themes": data.get("ai_themes") or [],
        "editorial_policy": data.get("editorial_policy") or {},
    }


@router.get("/source-rights")
def logos_source_rights(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    data = _data()
    return {
        "policy": data.get("editorial_policy") or {},
        "items": data.get("sources") or [],
        "count": len(data.get("sources") or []),
    }


@router.get("/passage")
def logos_passage(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return _passage_payload(_passage(reference))


@router.get("/interlinear")
def logos_interlinear(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "no-store, max-age=0"
    item = _passage(reference)
    interlinear = item.get("interlinear") or {}
    return {
        "reference": item.get("reference"),
        "language": interlinear.get("language"),
        "label": interlinear.get("label"),
        "tokens": interlinear.get("tokens") or [],
        "note": "Morphology and glosses are study aids. They must remain tied to a pinned textual edition when the full corpus is imported.",
    }


@router.get("/commentary")
def logos_commentary(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "no-store, max-age=0"
    item = _passage(reference)
    return {
        "reference": item.get("reference"),
        "commentary": item.get("commentary") or {},
        "jerome_biblical_commentary": {
            "status": "reference-only",
            "full_text_included": False,
            "reason": "Copyright/permission gate: bibliographic reference is allowed, but full text is not bundled without a suitable license or permission.",
        },
        "method_note": "Editorial commentary, patristic material and AI synthesis are kept distinct from the biblical text itself.",
    }


@router.get("/fathers")
def logos_fathers(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "no-store, max-age=0"
    item = _passage(reference)
    return {
        "reference": item.get("reference"),
        "fathers": item.get("fathers") or [],
        "catena_aurea": item.get("catena") or [],
        "rights_note": "Full patristic texts are enabled only source-by-source after edition and translation rights are recorded.",
    }


@router.get("/preacher")
def logos_preacher(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "no-store, max-age=0"
    item = _passage(reference)
    return {
        "reference": item.get("reference"),
        "outline": item.get("preacher") or {},
        "editorial_note": "These Mercy outlines are original study scaffolds. They are not copied from a copyrighted preacher's manual.",
    }


@router.get("/places")
def logos_places(reference: str | None = Query(default=None, max_length=120), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    places = list(_data().get("places") or [])
    if reference:
        needle = _normalize_reference(reference)
        book = needle.split(" ", 1)[0]
        exact = [
            place
            for place in places
            if any(needle in _normalize_reference(ref) or book in _normalize_reference(ref) for ref in place.get("references") or [])
        ]
        if exact:
            places = exact
    return {
        "items": places,
        "count": len(places),
        "method_note": "Coordinates and archaeological notes are orientation aids. Site identifications and excavation claims must be sourced individually before publication as definitive findings.",
    }


@router.get("/media")
def logos_media(kind: str | None = Query(default=None, max_length=40), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    items = _all_media()
    if kind:
        items = [row for row in items if row.get("kind") == kind]
    return {
        "items": items,
        "count": len(items),
        "rights_note": "Every displayed image carries a source URL and rights/credit field. Local mirroring should occur only after its file-page license is verified.",
    }


@router.post("/ai")
def logos_ai(payload: LogosAIIn, request: Request):
    data = _data()
    themes = {str(row.get("id")): str(row.get("label")) for row in data.get("ai_themes") or []}
    if payload.theme not in themes:
        raise HTTPException(status_code=400, detail="invalid_logos_theme")

    local_context = ""
    try:
        item = _passage(payload.reference)
        p = _passage_payload(item)
        rendered = []
        for code in ("en", "he", "la", "arc", "grc"):
            row = p.get("languages", {}).get(code)
            if row and row.get("text"):
                rendered.append(f"{row.get('label', code)}: {row.get('text')}")
        if rendered:
            local_context = "\nLocal deterministic text context:\n" + "\n".join(rendered)
    except HTTPException:
        item = None

    extra = (payload.question or "").strip()
    prompt = f"""LOGOS BIBLICAL STUDY REQUEST
Reference: {payload.reference.strip()}
Theme: {themes[payload.theme]}
{local_context}
User focus: {extra or 'Use the selected theme only.'}

Answer as a Catholic biblical-study assistant. Distinguish Scripture text, lexical/grammatical observation, historical or archaeological evidence, patristic interpretation, Magisterial teaching, modern scholarship, and your own synthesis. Do not invent manuscript readings, archaeological discoveries, Father quotations, commentary quotations, page numbers or citations. If a source is uncertain or disputed, say so. For original-language analysis, state whether the language is an original-language witness for that biblical book or a later translation. Do not reproduce substantial text from the Jerome Biblical Commentary or other modern copyrighted commentaries; summarize only when legitimately supported. For homily or Bible-study outlines, produce an original outline rather than imitating a copyrighted manual."""

    if len(prompt) > 1950:
        prompt = prompt[:1950]
    return ask_magisterium(
        CatholicChatIn(message=prompt, language=payload.language),
        _client_key(request),
    )
