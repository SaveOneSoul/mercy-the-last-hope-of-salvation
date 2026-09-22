from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from .logos import _client_key, _parse_corpus_reference, _passage, _passage_payload
from .logos_context import ADVANCED_AI_THEMES, build_background, build_chronology, build_traditions
from .logos_greek import router as logos_greek_router
from .logos_ot_greek import router as logos_ot_greek_router
from .logos_ot_greek_full import router as logos_ot_greek_full_router
from .logos_ot_greek_linguistics import router as logos_ot_greek_linguistics_router
from .logos_ot_interlinear import router as logos_ot_interlinear_router
from .logos_ot_latin import router as logos_ot_latin_router
from .logos_nt_tagnt_linguistics import router as logos_nt_tagnt_linguistics_router
from .logos_ot_semitic import router as logos_ot_semitic_router
from .magisterium import CatholicChatIn, ask_magisterium


router = APIRouter(prefix="/api/logos", tags=["Logos Advanced Study"])
router.include_router(logos_greek_router)
router.include_router(logos_ot_greek_router)
router.include_router(logos_ot_greek_full_router)
router.include_router(logos_ot_greek_linguistics_router)
router.include_router(logos_ot_semitic_router)
router.include_router(logos_ot_latin_router)
router.include_router(logos_nt_tagnt_linguistics_router)
router.include_router(logos_ot_interlinear_router)
ADVANCED_THEME_MAP = {str(row["id"]): str(row["label"]) for row in ADVANCED_AI_THEMES}


class LogosAdvancedAIIn(BaseModel):
    reference: str = Field(min_length=2, max_length=120)
    theme: str = Field(min_length=2, max_length=80)
    question: str | None = Field(default=None, max_length=1000)
    language: str = Field(default="en", pattern="^(en|kha)$")


def _no_store(response: Response | None) -> None:
    if response is not None:
        response.headers["Cache-Control"] = "no-store, max-age=0"


def _advanced_item(reference: str) -> dict:
    item = _passage(reference)
    if not item.get("book_id"):
        book_meta, _, _, _ = _parse_corpus_reference(item.get("reference") or reference)
        item["book_id"] = book_meta.get("id")
    return item


@router.get("/background")
def logos_background(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    _no_store(response)
    return build_background(_advanced_item(reference))


@router.get("/chronology")
def logos_chronology(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    _no_store(response)
    return build_chronology(_advanced_item(reference))


@router.get("/traditions")
def logos_traditions(reference: str = Query(min_length=2, max_length=120), response: Response = None):
    _no_store(response)
    return build_traditions(_advanced_item(reference))


@router.post("/advanced-ai")
def logos_advanced_ai(payload: LogosAdvancedAIIn, request: Request):
    if payload.theme not in ADVANCED_THEME_MAP:
        raise HTTPException(status_code=400, detail="invalid_logos_advanced_theme")

    item = _advanced_item(payload.reference)
    passage = _passage_payload(item)
    background = build_background(item)
    chronology = build_chronology(item)

    english = ((passage.get("languages") or {}).get("en") or {}).get("text") or ""
    profile = background.get("book_profile") or {}
    testament = background.get("testament_background") or {}
    evidence_lenses = chronology.get("archive_lenses") or []
    focus = (payload.question or "").strip() or "Use the selected theme only."

    prompt = f"""LOGOS ADVANCED BIBLICAL STUDY REQUEST
Reference: {passage.get('reference') or payload.reference.strip()}
Theme: {ADVANCED_THEME_MAP[payload.theme]}
English deterministic Scripture text: {english}
Book: {background.get('book')}
Testament: {background.get('testament')}
Genre: {profile.get('genre', 'Not specified')}
Book historical setting: {profile.get('historical_setting', 'Not specified')}
Book audience: {profile.get('audience', 'Not specified')}
Book theological focus: {profile.get('theological_focus', 'Not specified')}
Testament historical frame: {testament.get('historical_background', '')}
Testament theological frame: {testament.get('theological_background', '')}
Potential secular-history / archive lenses: {'; '.join(evidence_lenses)}
User focus: {focus}

Answer as a Catholic biblical-study assistant. Begin from the literal sense and the supplied deterministic Scripture text. Distinguish clearly: (1) biblical text, (2) literary/grammatical observation, (3) historical reconstruction, (4) secular historical or archaeological evidence, (5) Jewish interpretive context, (6) patristic/Catholic tradition, (7) authoritative Magisterial teaching when genuinely applicable, (8) other Christian commentary traditions, and (9) your synthesis. For audience, authorship, date, chronology and historical setting, state when a point is traditional, probable, disputed or unknown. Never invent royal-annal entries, inscriptions, archaeological finds, quotations, manuscript readings, page numbers or source citations. Do not use archaeology or secular archives as proof of theology. For Jewish interpretation, distinguish ancient Jewish context from later rabbinic or medieval commentary. For Protestant, Evangelical or Orthodox interpretations, identify the tradition and do not present it as Catholic Magisterial teaching. Do not reproduce substantial hosted text from e-Catholic 2000 or modern copyrighted commentaries. If a requested claim cannot be supported, say that evidence is insufficient."""

    if len(prompt) > 9000:
        prompt = prompt[:9000]
    return ask_magisterium(CatholicChatIn(message=prompt, language=payload.language), _client_key(request))
