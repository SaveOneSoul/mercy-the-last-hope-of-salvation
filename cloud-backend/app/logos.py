import copy
import json
import re
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Request, Response
from pydantic import BaseModel, Field

from .magisterium import CatholicChatIn, ask_magisterium

router = APIRouter(prefix="/api/logos", tags=["Logos"])
DATA_PATH = Path(__file__).with_name("logos_seed.json")
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "eng_douay_rheims_1899"
CORPUS_MANIFEST_PATH = CORPUS_DIR / "manifest.json"


class LogosAIIn(BaseModel):
    reference: str = Field(min_length=2, max_length=120)
    theme: str = Field(min_length=2, max_length=80)
    question: str | None = Field(default=None, max_length=1000)
    language: str = Field(default="en", pattern="^(en|kha)$")


@lru_cache(maxsize=1)
def _data() -> dict:
    with DATA_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


@lru_cache(maxsize=1)
def _corpus_manifest() -> dict:
    if not CORPUS_MANIFEST_PATH.exists():
        return {}
    with CORPUS_MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if int(manifest.get("book_count") or 0) != 73:
        raise RuntimeError("Logos English corpus manifest does not contain the 73-book Catholic canon")
    return manifest


@lru_cache(maxsize=24)
def _corpus_book(filename: str) -> dict:
    safe_name = Path(filename).name
    if safe_name != filename or not safe_name.endswith(".json"):
        raise RuntimeError("Invalid Logos corpus filename")
    path = CORPUS_DIR / safe_name
    if not path.exists():
        raise RuntimeError(f"Logos corpus book file missing: {safe_name}")
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or "unknown"
    return request.client.host if request.client else "unknown"


def _normalize_reference(value: str) -> str:
    value = re.sub(r"[.]+", "", (value or "").strip())
    value = value.replace("–", "-").replace("—", "-")
    value = re.sub(r"\s+", " ", value).lower()
    value = re.sub(r"\s*:\s*", ":", value)
    value = re.sub(r"\s*-\s*", "-", value)
    return value


def _source_index() -> dict[str, dict]:
    rows = {str(item.get("id")): copy.deepcopy(item) for item in _data().get("sources", [])}
    manifest = _corpus_manifest()
    translation = manifest.get("translation") or {}
    source = manifest.get("source") or {}
    if manifest and translation.get("id"):
        source_id = str(translation["id"])
        row = rows.setdefault(source_id, {"id": source_id})
        row.update(
            {
                "title": translation.get("title") or row.get("title"),
                "category": "scripture",
                "language": translation.get("language", "en"),
                "status": "approved-installed",
                "rights": translation.get("rights", "public-domain"),
                "allowed_display_scope": translation.get("allowed_display_scope", "full-text"),
                "edition_note": "Full 73-book Catholic English corpus is vendored locally and integrity-locked.",
                "provenance_url": translation.get("upstream_rights_url"),
                "corpus_version": manifest.get("corpus_version"),
                "source_commit": source.get("mirror_commit"),
                "source_git_blob_sha1": source.get("git_blob_sha1"),
                "source_sha256": source.get("download_sha256"),
            }
        )
    return rows


def _source_for(source_id: str | None) -> dict | None:
    if not source_id:
        return None
    return _source_index().get(source_id)


def _book_alias_index() -> dict[str, dict]:
    index: dict[str, dict] = {}
    for row in _corpus_manifest().get("books") or []:
        aliases = set(row.get("aliases") or [])
        aliases.add(str(row.get("name") or ""))
        aliases.add(str(row.get("id") or ""))
        for alias in aliases:
            normalized = _normalize_reference(alias)
            if normalized:
                index[normalized] = row
    return index


def _parse_corpus_reference(reference: str) -> tuple[dict, int, int | None, int | None]:
    normalized = _normalize_reference(reference)
    aliases = _book_alias_index()
    for alias in sorted(aliases, key=len, reverse=True):
        if normalized == alias:
            raise HTTPException(status_code=400, detail="logos_reference_requires_chapter")
        prefix = alias + " "
        if not normalized.startswith(prefix):
            continue
        remainder = normalized[len(prefix) :].strip()
        match = re.fullmatch(r"(\d+)(?::(\d+)(?:-(\d+))?)?", remainder)
        if not match:
            raise HTTPException(status_code=400, detail="logos_reference_invalid")
        chapter = int(match.group(1))
        verse_start = int(match.group(2)) if match.group(2) else None
        verse_end = int(match.group(3)) if match.group(3) else verse_start
        if chapter < 1 or (verse_start is not None and verse_start < 1):
            raise HTTPException(status_code=400, detail="logos_reference_invalid")
        if verse_start is not None and verse_end is not None and verse_end < verse_start:
            raise HTTPException(status_code=400, detail="logos_reference_invalid")
        if verse_start is not None and verse_end is not None and verse_end - verse_start > 100:
            raise HTTPException(status_code=400, detail="logos_reference_range_too_large")
        return aliases[alias], chapter, verse_start, verse_end
    raise HTTPException(status_code=404, detail="logos_book_not_in_catholic_canon")


def _verse_number(verse_id: str) -> int:
    match = re.match(r"(\d+)", str(verse_id))
    return int(match.group(1)) if match else 10**9


def _find_verse(chapter: dict[str, str], verse: int) -> tuple[str, str] | None:
    direct = chapter.get(str(verse))
    if direct:
        return str(verse), direct
    for verse_id, text in chapter.items():
        match = re.fullmatch(r"(\d+)-(\d+)", str(verse_id))
        if match and int(match.group(1)) <= verse <= int(match.group(2)):
            return str(verse_id), text
    return None


def _corpus_passage(reference: str) -> dict:
    manifest = _corpus_manifest()
    if not manifest:
        raise HTTPException(status_code=404, detail="logos_english_corpus_not_installed")
    book_meta, chapter_number, verse_start, verse_end = _parse_corpus_reference(reference)
    book = _corpus_book(str(book_meta.get("filename")))
    chapter = (book.get("chapters") or {}).get(str(chapter_number))
    if not chapter:
        raise HTTPException(status_code=404, detail="logos_chapter_not_found")

    selected: list[dict] = []
    if verse_start is None:
        for verse_id, text in sorted(chapter.items(), key=lambda item: _verse_number(item[0])):
            if text:
                selected.append({"verse": verse_id, "text": text})
    else:
        seen_ids: set[str] = set()
        for verse in range(verse_start, (verse_end or verse_start) + 1):
            found = _find_verse(chapter, verse)
            if not found:
                raise HTTPException(status_code=404, detail="logos_verse_not_found")
            verse_id, text = found
            if verse_id not in seen_ids:
                selected.append({"verse": verse_id, "text": text})
                seen_ids.add(verse_id)

    if not selected:
        raise HTTPException(status_code=404, detail="logos_passage_not_found")

    canonical_book = str(book_meta.get("name"))
    if verse_start is None:
        canonical_reference = f"{canonical_book} {chapter_number}"
    elif verse_end and verse_end != verse_start:
        canonical_reference = f"{canonical_book} {chapter_number}:{verse_start}-{verse_end}"
    else:
        canonical_reference = f"{canonical_book} {chapter_number}:{verse_start}"

    if len(selected) == 1:
        rendered_text = selected[0]["text"]
    else:
        rendered_text = " ".join(f"{row['verse']} {row['text']}" for row in selected)

    return {
        "reference": canonical_reference,
        "book": canonical_book,
        "book_id": book_meta.get("id"),
        "testament": book_meta.get("testament"),
        "chapter": chapter_number,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "verses": selected,
        "languages": {
            "en": {
                "label": "English — Douay-Rheims 1899",
                "source_id": "drb-challoner",
                "status": "available",
                "text": rendered_text,
                "note": "Public-domain 73-book Catholic corpus vendored from the pinned eBible engDRA source.",
            }
        },
        "interlinear": {},
        "commentary": {},
        "fathers": [],
        "catena": [],
        "preacher": {},
        "corpus": "eng_douay_rheims_1899",
    }


def _seed_passage(reference: str) -> dict | None:
    key = _normalize_reference(reference)
    item = _data().get("passages", {}).get(key)
    return copy.deepcopy(item) if item else None


def _passage(reference: str) -> dict:
    corpus_item = _corpus_passage(reference)
    seed_item = _seed_passage(corpus_item.get("reference") or reference)
    if not seed_item:
        return corpus_item

    # Keep curated Greek/Hebrew/Latin, interlinear and study material for seed
    # references, but make the vendored English corpus authoritative for English.
    seed_item["reference"] = corpus_item["reference"]
    seed_item["book"] = corpus_item["book"]
    seed_item["book_id"] = corpus_item["book_id"]
    seed_item["testament"] = corpus_item["testament"]
    seed_item["chapter"] = corpus_item.get("chapter")
    seed_item["verse_start"] = corpus_item.get("verse_start")
    seed_item["verse_end"] = corpus_item.get("verse_end")
    seed_item["verses"] = corpus_item.get("verses") or []
    seed_item["corpus"] = corpus_item.get("corpus")
    seed_item.setdefault("languages", {})["en"] = corpus_item["languages"]["en"]
    return seed_item


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
                "corpus_version": source.get("corpus_version"),
            }
        languages[code] = entry
    return {
        "reference": item.get("reference"),
        "book": item.get("book"),
        "book_id": item.get("book_id"),
        "testament": item.get("testament"),
        "chapter": item.get("chapter"),
        "verse_start": item.get("verse_start"),
        "verse_end": item.get("verse_end"),
        "verses": item.get("verses") or [],
        "languages": languages,
        "available_language_codes": [code for code, row in languages.items() if row.get("text")],
        "rights_notice": _data().get("editorial_policy", {}).get("rule"),
    }


@lru_cache(maxsize=1)
def _search_rows() -> tuple[dict, ...]:
    rows: list[dict] = []
    for meta in _corpus_manifest().get("books") or []:
        book = _corpus_book(str(meta.get("filename")))
        for chapter_id, verses in (book.get("chapters") or {}).items():
            if not isinstance(verses, dict):
                continue
            for verse_id, text in verses.items():
                rendered = str(text or "").strip()
                if not rendered:
                    continue
                rows.append(
                    {
                        "reference": f"{meta.get('name')} {chapter_id}:{verse_id}",
                        "book": meta.get("name"),
                        "book_id": meta.get("id"),
                        "testament": meta.get("testament"),
                        "chapter": str(chapter_id),
                        "verse": str(verse_id),
                        "text": rendered,
                        "_search": rendered.casefold(),
                    }
                )
    return tuple(rows)


def _all_media() -> list[dict]:
    return list(_data().get("media") or [])


@router.get("/catalog")
def logos_catalog(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    data = _data()
    manifest = _corpus_manifest()
    return {
        "module": "Logos — Biblical Study & Catholic Exegesis",
        "version": manifest.get("corpus_version") or data.get("version"),
        "canon": "Catholic 73-book canon",
        "book_count": int(manifest.get("book_count") or len(data.get("books") or [])),
        "books": manifest.get("books") or data.get("books") or [],
        "english_corpus": {
            "installed": bool(manifest),
            "translation": (manifest.get("translation") or {}).get("title"),
            "book_count": manifest.get("book_count", 0),
            "chapter_count": manifest.get("chapter_count", 0),
            "verse_count": manifest.get("verse_count", 0),
            "corpus_version": manifest.get("corpus_version"),
            "integrity": (manifest.get("source") or {}).get("integrity"),
        },
        "curated_parallel_references": [row.get("reference") for row in (data.get("passages") or {}).values()],
        "ai_themes": data.get("ai_themes") or [],
        "editorial_policy": data.get("editorial_policy") or {},
    }


@router.get("/search")
def logos_search(
    q: str = Query(min_length=2, max_length=120),
    limit: int = Query(default=40, ge=1, le=100),
    response: Response = None,
):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=120"

    query = re.sub(r"\s+", " ", q.strip())
    if not query:
        raise HTTPException(status_code=400, detail="logos_search_query_required")

    # Prefer canonical reference resolution when the query is itself a reference.
    if any(ch.isdigit() for ch in query):
        try:
            passage = _corpus_passage(query)
        except HTTPException:
            passage = None
        if passage:
            results = [
                {
                    "reference": f"{passage['book']} {passage['chapter']}:{row['verse']}",
                    "book": passage["book"],
                    "book_id": passage["book_id"],
                    "testament": passage["testament"],
                    "chapter": str(passage["chapter"]),
                    "verse": str(row["verse"]),
                    "text": row["text"],
                }
                for row in passage.get("verses") or []
            ]
            return {
                "query": query,
                "mode": "reference",
                "count": len(results),
                "has_more": False,
                "results": results[:limit],
            }

    terms = [term for term in query.casefold().split(" ") if term]
    results: list[dict] = []
    has_more = False
    for row in _search_rows():
        haystack = row["_search"]
        if all(term in haystack for term in terms):
            if len(results) >= limit:
                has_more = True
                break
            results.append({key: value for key, value in row.items() if key != "_search"})

    return {
        "query": query,
        "mode": "text",
        "count": len(results),
        "has_more": has_more,
        "results": results,
    }


@router.get("/source-rights")
def logos_source_rights(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    data = _data()
    items = list(_source_index().values())
    return {
        "policy": data.get("editorial_policy") or {},
        "items": items,
        "count": len(items),
        "english_corpus_manifest": _corpus_manifest(),
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
        "label": interlinear.get("label") or "Interlinear",
        "tokens": interlinear.get("tokens") or [],
        "note": (
            "Morphology and glosses are available only for references with a pinned original-language "
            "dataset. The full English Bible is installed independently of the Hebrew/Greek interlinear corpus."
        ),
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
        "method_note": "The full English Scripture corpus is independent of editorial commentary. Curated commentary is added passage-by-passage and AI synthesis remains separately identified.",
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
        "editorial_note": "Mercy preacher outlines are original study scaffolds and are added independently of the complete Bible text. Magisterium AI can create a new outline for any installed passage.",
    }


@router.get("/places")
def logos_places(reference: str | None = Query(default=None, max_length=120), response: Response = None):
    if response is not None:
        response.headers["Cache-Control"] = "public, max-age=300"
    places = list(_data().get("places") or [])
    if reference:
        needle = _normalize_reference(reference)
        try:
            book_meta, _, _, _ = _parse_corpus_reference(reference)
            book_name = _normalize_reference(str(book_meta.get("name") or ""))
        except HTTPException:
            book_name = needle.split(" ", 1)[0]
        exact = [
            place
            for place in places
            if any(
                needle in _normalize_reference(ref) or book_name in _normalize_reference(ref)
                for ref in place.get("references") or []
            )
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

    item = _passage(payload.reference)
    passage = _passage_payload(item)
    rendered = []
    for code in ("en", "he", "la", "arc", "grc"):
        row = passage.get("languages", {}).get(code)
        if row and row.get("text"):
            rendered.append(f"{row.get('label', code)}: {row.get('text')}")
    local_context = "\nLocal deterministic text context:\n" + "\n".join(rendered) if rendered else ""

    extra = (payload.question or "").strip()
    prompt = f"""LOGOS BIBLICAL STUDY REQUEST
Reference: {passage.get('reference') or payload.reference.strip()}
Theme: {themes[payload.theme]}
{local_context}
User focus: {extra or 'Use the selected theme only.'}

Answer as a Catholic biblical-study assistant. Treat the local Douay-Rheims text above as the deterministic English Scripture context when supplied. Distinguish Scripture text, lexical/grammatical observation, historical or archaeological evidence, patristic interpretation, Magisterial teaching, modern scholarship, and your own synthesis. Do not invent manuscript readings, archaeological discoveries, Father quotations, commentary quotations, page numbers or citations. If a source is uncertain or disputed, say so. For original-language analysis, state whether the language is an original-language witness for that biblical book or a later translation. Do not reproduce substantial text from the Jerome Biblical Commentary or other modern copyrighted commentaries; summarize only when legitimately supported. For homily or Bible-study outlines, produce an original outline rather than imitating a copyrighted manual."""

    if len(prompt) > 6000:
        prompt = prompt[:6000]
    return ask_magisterium(
        CatholicChatIn(message=prompt, language=payload.language),
        _client_key(request),
    )
