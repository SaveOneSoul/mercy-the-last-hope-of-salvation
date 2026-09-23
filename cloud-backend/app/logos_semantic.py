from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _corpus_passage, _parse_corpus_reference
from .logos_greek import _interlinear_payload as _greek_nt_payload
from .logos_ot_greek_linguistics import _book as _rahlfs_book
from .logos_ot_semitic import _study_payload as _semitic_payload


router = APIRouter(prefix="/semantic", tags=["Logos 73-book Semantic Interlinear"])
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "semantic_stepbible"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"

GREEK_MAP = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z",
    "η": "ē", "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m",
    "ν": "n", "ξ": "x", "ο": "o", "π": "p", "ρ": "r", "σ": "s",
    "ς": "s", "τ": "t", "υ": "y", "φ": "ph", "χ": "ch", "ψ": "ps",
    "ω": "ō",
}
ROUGH_BREATHING = "\u0314"
IOTA_SUBSCRIPT = "\u0345"
SOURCE_REF_RE = re.compile(r"^.+?\s+(\d+):(.+)$")


@lru_cache(maxsize=1)
def _manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    payload = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if payload.get("corpus_id") != "logos_stepbible_semantics":
        raise RuntimeError("Unexpected Logos semantic corpus id")
    if payload.get("production_enabled") is not True:
        raise RuntimeError("Logos semantic corpus is not production-enabled")
    coverage = payload.get("coverage") or {}
    if int(coverage.get("semantic_book_coverage") or 0) != 73:
        raise RuntimeError("Logos semantic corpus does not cover 73 books")
    runtime = payload.get("runtime_contract") or {}
    if runtime.get("rahlfs_remains_separate_from_swete") is not True:
        raise RuntimeError("Rahlfs/Swete semantic boundary changed")
    if runtime.get("hebrew_restricted_meaning_field_excluded") is not True:
        raise RuntimeError("Hebrew semantic rights boundary changed")
    return payload


def _require_installed() -> dict:
    manifest = _manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="logos_semantic_corpus_not_installed")
    return manifest


@lru_cache(maxsize=1)
def _greek_lexicon() -> dict:
    _require_installed()
    return json.loads((CORPUS_DIR / "lexicon" / "greek.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _hebrew_lexicon() -> dict:
    _require_installed()
    return json.loads((CORPUS_DIR / "lexicon" / "hebrew.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _greek_morphology() -> dict:
    _require_installed()
    return json.loads((CORPUS_DIR / "morphology" / "greek.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def _hebrew_morphology() -> dict:
    _require_installed()
    return json.loads((CORPUS_DIR / "morphology" / "hebrew.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=96)
def _context(kind: str, book_id: str) -> dict:
    if kind not in {"nt", "ot-semitic"}:
        raise RuntimeError("invalid semantic context kind")
    safe = "".join(ch for ch in str(book_id).upper() if ch.isalnum())
    if safe != str(book_id).upper():
        raise RuntimeError("invalid semantic context book id")
    path = CORPUS_DIR / "context" / kind / f"{safe}.json"
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _normalize_greek(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or "").casefold())
    return "".join(
        ch for ch in text
        if ch.isalpha() and not unicodedata.category(ch).startswith("M")
    )


def _normalize_hebrew(value: str) -> str:
    text = unicodedata.normalize("NFD", str(value or ""))
    return "".join(
        ch for ch in text
        if "\u0590" <= ch <= "\u05ff"
        and not unicodedata.category(ch).startswith("M")
    )


def _transliterate_greek(surface: str) -> str:
    decomposed = unicodedata.normalize("NFD", str(surface or ""))
    rough = ROUGH_BREATHING in decomposed
    first_base_upper = False
    base_seen = False
    out: list[str] = []
    for char in decomposed:
        if char == IOTA_SUBSCRIPT:
            out.append("i")
            continue
        if unicodedata.category(char).startswith("M"):
            continue
        mapped = GREEK_MAP.get(char.lower())
        if mapped is None:
            continue
        if not base_seen:
            first_base_upper = char.isupper()
            base_seen = True
        out.append(mapped)
    result = "".join(out)
    if rough and result:
        result = ("rh" + result[1:]) if result.startswith("r") else ("h" + result)
    if first_base_upper and result:
        result = result[0].upper() + result[1:]
    return result


def _entry_by_strong(payload: dict, strong: str | None) -> dict | None:
    if not strong:
        return None
    indexes = (payload.get("strong_index") or {}).get(strong) or []
    if not indexes and strong.startswith("H") and strong[1:].isdigit():
        padded = f"H{int(strong[1:]):04d}"
        indexes = (payload.get("strong_index") or {}).get(padded) or []
    if not indexes:
        return None
    entries = payload.get("entries") or []
    candidates = [entries[int(index)] for index in indexes if int(index) < len(entries)]
    if not candidates:
        return None
    for row in candidates:
        if row.get("d_strong") == strong:
            return row
    return candidates[0]


def _greek_entry_by_lemma(lemma: str | None) -> dict | None:
    if not lemma:
        return None
    lexicon = _greek_lexicon()
    indexes = (lexicon.get("lemma_index") or {}).get(_normalize_greek(lemma)) or []
    if not indexes:
        return None
    entries = lexicon.get("entries") or []
    return entries[int(indexes[0])] if int(indexes[0]) < len(entries) else None


def _morphology(language: str, code: str | None) -> dict:
    if not code:
        return {"code": None, "summary": None, "features": None, "explanation": None, "example": None}
    source = _greek_morphology() if language == "grc" else _hebrew_morphology()
    row = (source.get("records") or {}).get(code) or {}
    return {
        "code": code,
        "summary": row.get("summary"),
        "features": row.get("features"),
        "explanation": row.get("explanation"),
        "example": row.get("example"),
    }


def _align_context(source_tokens: list[dict], context_tokens: list[dict], language: str) -> dict[str, dict]:
    if not source_tokens or not context_tokens:
        return {}
    normalize = _normalize_greek if language == "grc" else _normalize_hebrew
    output: dict[str, dict] = {}
    used: set[int] = set()

    # First prefer verified same-position surface identity.
    for idx, token in enumerate(source_tokens):
        if idx >= len(context_tokens):
            break
        ctx = context_tokens[idx]
        if normalize(token.get("surface")) and normalize(token.get("surface")) == normalize(ctx.get("surface")):
            token_id = str(token.get("id") or "")
            if token_id:
                output[token_id] = ctx
                used.add(idx)

    # Then use a monotonic surface match for presentation/segmentation differences.
    cursor = 0
    for token in source_tokens:
        token_id = str(token.get("id") or "")
        if not token_id or token_id in output:
            continue
        key = normalize(token.get("surface"))
        if not key:
            continue
        for idx in range(cursor, len(context_tokens)):
            if idx in used:
                continue
            if normalize(context_tokens[idx].get("surface")) == key:
                output[token_id] = context_tokens[idx]
                used.add(idx)
                cursor = idx + 1
                break
    return output


def _lexical_payload(entry: dict | None, *, include_meaning: bool) -> dict:
    if not entry:
        return {
            "strong": None,
            "lemma": None,
            "transliteration": None,
            "gloss": None,
            "meaning": None,
            "status": "not-found-in-pinned-lexicon",
        }
    return {
        "strong": entry.get("d_strong") or entry.get("e_strong"),
        "e_strong": entry.get("e_strong"),
        "d_strong": entry.get("d_strong"),
        "u_strong": entry.get("u_strong"),
        "lemma": entry.get("lemma"),
        "transliteration": entry.get("transliteration"),
        "gloss": entry.get("gloss"),
        "meaning": entry.get("meaning") if include_meaning else None,
        "status": "available",
    }


def _english(reference: str) -> dict:
    passage = _corpus_passage(reference)
    return {
        "translation": "Douay-Rheims American Edition (1899)",
        "reference": passage.get("reference"),
        "verses": passage.get("verses") or [],
        "note": (
            "The Douay-Rheims is the primary Catholic English reading lane. "
            "Original-language contextual glosses below are semantic aids and are not asserted as a one-to-one Douay word alignment."
        ),
    }


def _nt_semantics(reference: str, book_id: str) -> dict:
    greek = _greek_nt_payload(reference)
    context_book = _context("nt", book_id)
    context_verses = context_book.get("verses") or {}
    lexicon = _greek_lexicon()

    ling_by_id = {
        str(token.get("id")): token
        for verse in ((greek.get("linguistics") or {}).get("verses") or [])
        for token in (verse.get("tokens") or [])
    }

    verses = []
    for verse in ((greek.get("surface") or {}).get("verses") or []):
        canonical_verse = str(verse.get("verse"))
        aligned: dict[str, dict] = {}
        for source_row in verse.get("source_verses") or []:
            source_tokens = source_row.get("tokens") or []
            key = f"{int(source_row.get('chapter'))}:{int(source_row.get('verse'))}"
            aligned.update(_align_context(source_tokens, context_verses.get(key) or [], "grc"))

        words = []
        for token in verse.get("tokens") or []:
            token_id = str(token.get("id") or "")
            ling = ling_by_id.get(token_id) or {}
            # TAGNT context is not used as a replacement where MorphGNT annotation is absent.
            ctx = aligned.get(token_id) if ling else None
            strong = ctx.get("strong") if ctx else None
            lexical = _entry_by_strong(lexicon, strong) or _greek_entry_by_lemma(ling.get("lemma"))
            morph_code = ctx.get("morphology_code") if ctx else None
            words.append({
                "id": token_id,
                "position": token.get("position"),
                "surface": token.get("surface"),
                "transliteration": token.get("transliteration") or (ctx or {}).get("transliteration"),
                "lemma": ling.get("lemma"),
                "strong": strong,
                "part_of_speech": ling.get("part_of_speech_code"),
                "source_morphology": ling.get("morphology"),
                "grammar": _morphology("grc", morph_code),
                "lexical": _lexical_payload(lexical, include_meaning=True),
                "contextual_gloss": (ctx or {}).get("contextual_gloss"),
                "dictionary_gloss": (ctx or {}).get("dictionary_gloss"),
                "semantic_status": "context-source-backed" if ctx else ("lexical-only" if lexical else "linguistics-only"),
            })
        verses.append({
            "verse": canonical_verse,
            "source_missing": verse.get("source_missing", False),
            "mapping_relationship": verse.get("mapping_relationship"),
            "words": words,
        })

    return {
        "lane": "greek-nt-contextual",
        "label": "Greek New Testament — SBLGNT + MorphGNT + STEPBible semantics",
        "witness": "SBLGNT surface / MorphGNT linguistics",
        "semantic_source": "STEPBible TAGNT + TBESG + TEGMC",
        "alignment_policy": (
            "TAGNT semantic rows attach only after source-token surface verification and only where the pinned MorphGNT annotation exists."
        ),
        "verses": verses,
    }


def _semitic_semantics(reference: str, book_id: str) -> dict | None:
    try:
        semitic = _semitic_payload(reference)
    except HTTPException as exc:
        if exc.status_code == 404:
            return None
        raise
    context_book = _context("ot-semitic", book_id)
    context_verses = context_book.get("verses") or {}
    lexicon = _hebrew_lexicon()

    verses = []
    for verse in semitic.get("verses") or []:
        aligned: dict[str, dict] = {}
        for source_row in verse.get("source_verses") or []:
            source_tokens = source_row.get("tokens") or []
            key = f"{int(source_row.get('chapter'))}:{int(source_row.get('verse'))}"
            aligned.update(_align_context(source_tokens, context_verses.get(key) or [], "he"))

        words = []
        for token in verse.get("tokens") or []:
            token_id = str(token.get("id") or "")
            ctx = aligned.get(token_id)
            base_strong = None
            raw_lemma = str(token.get("lemma") or "")
            if raw_lemma.isdigit():
                base_strong = f"H{int(raw_lemma):04d}"
            strong = (ctx or {}).get("root_strong") or base_strong
            lexical = _entry_by_strong(lexicon, strong) or _entry_by_strong(lexicon, base_strong)
            morph_code = (ctx or {}).get("morphology_code") or token.get("morphology")
            words.append({
                "id": token_id,
                "position": token.get("position"),
                "surface": token.get("surface"),
                "language": token.get("language"),
                "transliteration": (ctx or {}).get("transliteration") or (lexical or {}).get("transliteration"),
                "lemma": token.get("lemma"),
                "strong": strong,
                "source_morphology": token.get("morphology"),
                "grammar": _morphology("he", morph_code),
                "lexical": _lexical_payload(lexical, include_meaning=False),
                "contextual_gloss": (ctx or {}).get("contextual_gloss"),
                "semantic_status": "context-source-backed" if ctx else ("lexical-only" if lexical else "linguistics-only"),
            })
        verses.append({
            "verse": str(verse.get("verse")),
            "source_osis_id": verse.get("source_osis_id"),
            "mapping_relationship": verse.get("mapping_relationship"),
            "source_missing": verse.get("source_missing", False),
            "words": words,
        })

    return {
        "lane": "hebrew-aramaic-contextual",
        "label": "Hebrew / Aramaic Old Testament — OSHB/WLC + STEPBible semantics",
        "witness": "OSHB/WLC",
        "semantic_source": "STEPBible TAHOT + TBESH + TEHMC",
        "alignment_policy": (
            "TAHOT semantic rows attach only after source-token surface verification. "
            "TBESH long Meaning text is excluded by rights policy; safe gloss/transliteration fields are used."
        ),
        "verses": verses,
    }


def _rahlfs_semantics(book_id: str, chapter: int, verse_number: int) -> dict:
    payload = _rahlfs_book(book_id)
    target = f"{chapter}:{verse_number}"
    selected = []
    for row in payload.get("verses") or []:
        ref = str(row.get("source_ref") or "")
        match = SOURCE_REF_RE.fullmatch(ref)
        if not match or f"{int(match.group(1))}:{match.group(2)}" != target:
            continue
        words = []
        for token in row.get("tokens") or []:
            lexical = _greek_entry_by_lemma(token.get("lemma"))
            words.append({
                "position": token.get("position"),
                "surface": token.get("surface"),
                "transliteration": _transliterate_greek(str(token.get("surface") or "")),
                "lemma": token.get("lemma"),
                "strong": (lexical or {}).get("d_strong") or (lexical or {}).get("e_strong"),
                "part_of_speech": token.get("part_of_speech"),
                "source_morphology": token.get("morphology"),
                "grammar": {
                    "code": None,
                    "summary": token.get("morphology") or token.get("part_of_speech"),
                    "features": token.get("reasoning"),
                    "explanation": None,
                    "example": None,
                },
                "lexical": _lexical_payload(lexical, include_meaning=True),
                "contextual_gloss": None,
                "semantic_status": "lexical-source-backed",
                "linguistic_confidence": token.get("confidence"),
                "linguistic_provenance": token.get("provenance_source"),
            })
        selected.append({
            "component": row.get("component"),
            "source_ref": ref,
            "words": words,
        })
    return {
        "lane": "greek-ot-rahlfs-lexical",
        "label": "Greek Old Testament — Rahlfs 1935/lxx-morph semantic witness",
        "witness": "Rahlfs Septuagint (1935), lxx-morph",
        "semantic_source": "lxx-morph + STEPBible TBESG",
        "alignment_policy": (
            "This is a separate source-native Rahlfs linguistic witness. A same-number source reference may be displayed for study, "
            "but it is NOT asserted to be the same verse identity as the Douay-Rheims or the installed Swete surface witness."
        ),
        "selection_mode": "source-native-same-numeric-reference-not-canonical-alignment",
        "requested_source_numeric": target,
        "source_matches": selected,
    }


@router.get("/catalog")
def semantic_catalog(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _require_installed()
    return {
        "installed": True,
        "production_enabled": manifest.get("production_enabled"),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "coverage": manifest.get("coverage") or {},
        "runtime_contract": manifest.get("runtime_contract") or {},
        "books": manifest.get("books") or [],
    }


@router.get("/source-rights")
def semantic_source_rights(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _require_installed()
    return {
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "source": manifest.get("source") or {},
        "rights_policy": manifest.get("rights_policy") or {},
        "runtime_contract": manifest.get("runtime_contract") or {},
    }


@router.get("/word-study")
def semantic_word_study(
    reference: str = Query(min_length=2, max_length=120),
    response: Response = None,
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=120"
    manifest = _require_installed()
    book_meta, chapter, verse_start, verse_end = _parse_corpus_reference(reference)
    if verse_start is None:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "logos_semantic_single_verse_required",
                "message": "Full original-language word study requires a verse reference, for example John 1:1 or Deuteronomy 6:4.",
            },
        )
    if verse_end is not None and verse_end != verse_start:
        raise HTTPException(
            status_code=400,
            detail={
                "code": "logos_semantic_single_verse_required",
                "message": "Select one verse at a time for full word-by-word semantic study.",
            },
        )

    book_id = str(book_meta.get("id"))
    testament = str(book_meta.get("testament"))
    canonical_reference = f"{book_meta.get('name')} {chapter}:{verse_start}"
    result = {
        "reference": canonical_reference,
        "book": book_meta.get("name"),
        "book_id": book_id,
        "testament": testament,
        "english": _english(canonical_reference),
        "semantic_policy": {
            "lexical_range_is_not_identical_to_contextual_sense": True,
            "contextual_gloss_source_backed_only": True,
            "contextual_gloss_is_not_douay_token_alignment": True,
            "no_fabricated_meaning": True,
        },
        "lanes": [],
        "coverage": (manifest.get("coverage") or {}),
    }

    if testament == "NT":
        result["lanes"].append(_nt_semantics(canonical_reference, book_id))
    else:
        semitic = _semitic_semantics(canonical_reference, book_id)
        if semitic:
            result["lanes"].append(semitic)
        result["lanes"].append(_rahlfs_semantics(book_id, chapter, verse_start))

    return result
