#!/usr/bin/env python3
"""Build the source-locked 73-book Logos semantic interlinear support corpus.

This layer enriches existing Logos witnesses; it never replaces or rewrites
the biblical text corpora.

Coverage model:
- 27 NT books: SBLGNT/MorphGNT remain the primary Greek witness; STEPBible
  TAGNT contributes context-sensitive gloss/Strong/grammar only when a token
  can be aligned to the preserved SBLGNT token.
- 39 Masoretic OT books: OSHB/WLC remains the Hebrew/Aramaic witness; STEPBible
  TAHOT contributes transliteration/contextual gloss/Strong/grammar only after
  token-surface verification.
- All 46 Catholic OT books: the existing Rahlfs 1935/lxx-morph corpus remains
  a separate Greek linguistic witness. TBESG supplies lexical lookup data, but
  no Rahlfs token is relabeled as Swete and no canonical versification identity
  is invented.

Important rights boundary:
TBESH's long "Meaning" field is deliberately NOT copied because TBESH itself
states that it derives from Abridged BDB/Online Bible and should not be applied
without separate permission. Safe STEPBible/Tyndale-created fields (Gloss,
Hebrew form, transliteration, morphology) are retained instead.
"""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import shutil
import time
import unicodedata
from collections import defaultdict
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "semantic_phase1" / "source-lock.json"
DEFAULT_OUTPUT = ROOT / "build" / "logos-semantic-interlinear-73"
PRODUCTION_OUTPUT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "semantic_stepbible"
BOOKS_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "books.json"
RAHLFS_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_ot_rahlfs_lxx_morph" / "books"

NT_BOOKS = {
    "Mat": "MAT", "Mrk": "MRK", "Luk": "LUK", "Jhn": "JHN", "Act": "ACT",
    "Rom": "ROM", "1Co": "1CO", "2Co": "2CO", "Gal": "GAL", "Eph": "EPH",
    "Php": "PHP", "Col": "COL", "1Th": "1TH", "2Th": "2TH", "1Ti": "1TI",
    "2Ti": "2TI", "Tit": "TIT", "Phm": "PHM", "Heb": "HEB", "Jas": "JAS",
    "1Pe": "1PE", "2Pe": "2PE", "1Jn": "1JN", "2Jn": "2JN", "3Jn": "3JN",
    "Jud": "JUD", "Rev": "REV",
}
OT_BOOKS = {
    "Gen": "GEN", "Exo": "EXO", "Lev": "LEV", "Num": "NUM", "Deu": "DEU",
    "Jos": "JOS", "Jdg": "JDG", "Rut": "RUT", "1Sa": "1SA", "2Sa": "2SA",
    "1Ki": "1KI", "2Ki": "2KI", "1Ch": "1CH", "2Ch": "2CH", "Ezr": "EZR",
    "Neh": "NEH", "Est": "EST", "Job": "JOB", "Psa": "PSA", "Pro": "PRO",
    "Ecc": "ECC", "Sng": "SNG", "Isa": "ISA", "Jer": "JER", "Lam": "LAM",
    "Ezk": "EZK", "Dan": "DAN", "Hos": "HOS", "Jol": "JOL", "Amo": "AMO",
    "Oba": "OBA", "Jon": "JON", "Mic": "MIC", "Nam": "NAM", "Hab": "HAB",
    "Zep": "ZEP", "Hag": "HAG", "Zec": "ZEC", "Mal": "MAL",
}
TAGNT_REF_RE = re.compile(r"^([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)#(\d+)=([^\t ]+)$")
TAHOT_REF_RE = re.compile(r"^([1-2]?[A-Za-z]+)\.(\d+)\.(\d+)#(\d+)=([^\t ]+)$")
STRONG_RE = re.compile(r"[GH]\d{4,5}[A-Z]?")
GREEK_LEX_RE = re.compile(r"^G\d{4,5}$")
HEBREW_LEX_RE = re.compile(r"^H\d{4,5}$")
TAG_SURFACE_RE = re.compile(r"^(.*?)\s+\((.*?)\)\s*$")


class BuildError(RuntimeError):
    pass


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise BuildError(f"cannot read {path}: {exc}") from exc


def write_json(path: Path, payload: dict, *, pretty: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if pretty:
        text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    else:
        text = json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n"
    path.write_text(text, encoding="utf-8")


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def download_pinned(repo: str, commit: str, path: str, expected_blob: str) -> tuple[str, str]:
    url = f"https://raw.githubusercontent.com/{repo}/{commit}/{quote(path, safe='/')}"
    request = Request(url, headers={"User-Agent": "Mercy-Logos-Semantic-Interlinear/1.0"})
    payload = None
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=90) as response:
                payload = response.read()
            break
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    if payload is None:
        raise BuildError(f"failed to download {repo}:{path}: {last_error}")
    actual = git_blob_sha1(payload)
    if actual != expected_blob:
        raise BuildError(f"Git blob mismatch for {path}: expected {expected_blob}, got {actual}")
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BuildError(f"source is not UTF-8: {path}") from exc
    return text, hashlib.sha256(payload).hexdigest()


def clean_markup(value: str) -> str:
    text = html.unescape(str(value or ""))
    text = re.sub(r"<[^>]*>", " ", text)
    text = text.replace("__", " ").replace("¶", " ")
    return re.sub(r"\s+", " ", text).strip()


def clean_context_gloss(value: str) -> str:
    text = str(value or "").replace("¶", "").strip()
    text = text.replace("<", "").replace(">", "").replace("[", "").replace("]", "")
    text = re.sub(r"\s*/\s*", " / ", text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_greek(value: str) -> str:
    value = unicodedata.normalize("NFD", str(value or "").casefold())
    chars = []
    for char in value:
        if unicodedata.category(char).startswith("M"):
            continue
        if unicodedata.category(char).startswith("P"):
            continue
        if char.isalpha():
            chars.append(char)
    return "".join(chars)


def first_strong(value: str) -> str | None:
    match = STRONG_RE.search(str(value or ""))
    return match.group(0) if match else None


def all_strongs(value: str) -> list[str]:
    seen = set()
    out = []
    for item in STRONG_RE.findall(str(value or "")):
        if item not in seen:
            seen.add(item)
            out.append(item)
    return out


def parse_greek_lexicon(text: str) -> dict:
    entries = []
    strong_index: dict[str, list[int]] = defaultdict(list)
    lemma_index: dict[str, list[int]] = defaultdict(list)
    for raw in text.splitlines():
        parts = raw.rstrip("\n").split("\t")
        if len(parts) < 8 or not GREEK_LEX_RE.fullmatch(parts[0].strip()):
            continue
        e_strong = parts[0].strip()
        d_strong = first_strong(parts[1])
        u_strong = first_strong(parts[2])
        greek = parts[3].strip()
        transliteration = parts[4].strip()
        morph = parts[5].strip()
        gloss = clean_markup(parts[6])
        meaning = clean_markup(parts[7])
        entry = {
            "e_strong": e_strong,
            "d_strong": d_strong,
            "u_strong": u_strong,
            "lemma": greek,
            "transliteration": transliteration,
            "lexical_morphology": morph,
            "gloss": gloss,
            "meaning": meaning,
        }
        index = len(entries)
        entries.append(entry)
        for alias in (e_strong, d_strong, u_strong):
            if alias and index not in strong_index[alias]:
                strong_index[alias].append(index)
        key = normalize_greek(greek)
        if key and index not in lemma_index[key]:
            lemma_index[key].append(index)
    if len(entries) < 10000:
        raise BuildError(f"Greek lexicon unexpectedly small: {len(entries)}")
    return {
        "schema_version": 1,
        "language": "grc",
        "entries": entries,
        "strong_index": dict(strong_index),
        "lemma_index": dict(lemma_index),
        "rights": {
            "license": "CC BY 4.0",
            "source": "STEPBible TBESG",
            "attribution": "STEP Bible / Tyndale House Cambridge",
        },
    }


def parse_hebrew_lexicon(text: str) -> dict:
    entries = []
    strong_index: dict[str, list[int]] = defaultdict(list)
    for raw in text.splitlines():
        parts = raw.rstrip("\n").split("\t")
        if len(parts) < 7 or not HEBREW_LEX_RE.fullmatch(parts[0].strip()):
            continue
        e_strong = parts[0].strip()
        d_strong = first_strong(parts[1])
        u_strong = first_strong(parts[2])
        entry = {
            "e_strong": e_strong,
            "d_strong": d_strong,
            "u_strong": u_strong,
            "lemma": parts[3].strip(),
            "transliteration": parts[4].strip(),
            "lexical_morphology": parts[5].strip(),
            "gloss": clean_markup(parts[6]),
        }
        # Deliberately do NOT copy parts[7] (TBESH Meaning).
        index = len(entries)
        entries.append(entry)
        for alias in (e_strong, d_strong, u_strong):
            if alias and index not in strong_index[alias]:
                strong_index[alias].append(index)
    if len(entries) < 8000:
        raise BuildError(f"Hebrew lexicon unexpectedly small: {len(entries)}")
    return {
        "schema_version": 1,
        "languages": ["he", "arc"],
        "entries": entries,
        "strong_index": dict(strong_index),
        "rights": {
            "license": "CC BY 4.0 for retained fields",
            "source": "STEPBible TBESH",
            "attribution": "STEP Bible / Tyndale House Cambridge",
            "excluded_field": "Meaning",
            "excluded_reason": (
                "TBESH says the long Meaning field is based on Abridged BDB/Online Bible "
                "and should not be applied without separate permission."
            ),
        },
    }


def parse_morphology(text: str, language: str) -> dict:
    lines = text.splitlines()
    try:
        start = next(i for i, line in enumerate(lines) if "FULL MORPHOLOGY CODES:" in line)
    except StopIteration as exc:
        raise BuildError(f"{language}: FULL MORPHOLOGY CODES section missing") from exc
    records: dict[str, dict] = {}
    i = start + 1
    while i < len(lines):
        if lines[i].strip() != "$":
            i += 1
            continue
        j = i + 1
        block = []
        while j < len(lines) and lines[j].strip() != "$":
            if lines[j].strip():
                block.append(lines[j].strip())
            j += 1
        if len(block) >= 4:
            code_line = block[0]
            code = code_line.split("\t", 1)[0].strip().strip('"')
            if code and len(code) <= 48 and not code.lower().startswith("code"):
                features = code_line.split("\t", 1)[1].strip() if "\t" in code_line else ""
                records[code] = {
                    "features": clean_markup(features),
                    "summary": clean_markup(block[1]),
                    "explanation": clean_markup(block[2]),
                    "example": clean_markup(block[3]),
                }
        i = j
    if len(records) < 100:
        raise BuildError(f"{language}: morphology expansion table unexpectedly small: {len(records)}")
    return {
        "schema_version": 1,
        "language": language,
        "records": records,
        "rights": {
            "license": "CC BY 4.0",
            "source": "STEPBible " + ("TEGMC" if language == "grc" else "TEHMC"),
            "attribution": "STEP Bible / Tyndale House Cambridge",
        },
    }


def parse_tagnt(texts: list[str]) -> tuple[dict[str, dict], int]:
    books: dict[str, dict[str, list[dict]]] = {book_id: defaultdict(list) for book_id in NT_BOOKS.values()}
    token_count = 0
    for text in texts:
        for raw in text.splitlines():
            if not raw or raw.startswith("#"):
                continue
            parts = raw.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            match = TAGNT_REF_RE.fullmatch(parts[0].strip())
            if not match:
                continue
            book_id = NT_BOOKS.get(match.group(1))
            if not book_id:
                continue
            editions = parts[5]
            if "SBL" not in editions:
                continue
            surface_field = parts[1].strip()
            surface_match = TAG_SURFACE_RE.fullmatch(surface_field)
            surface = surface_match.group(1).strip() if surface_match else surface_field
            transliteration = surface_match.group(2).strip() if surface_match else ""
            strong_grammar = parts[3].strip()
            strong, sep, morph_code = strong_grammar.partition("=")
            dictionary = parts[4].strip()
            source_lemma, lemma_sep, dictionary_gloss = dictionary.partition("=")
            row = {
                "source_position": int(match.group(4)),
                "word_type": match.group(5),
                "surface": surface,
                "transliteration": transliteration,
                "contextual_gloss": clean_context_gloss(parts[2]),
                "strong": first_strong(strong) or first_strong(strong_grammar),
                "morphology_code": morph_code.strip() if sep else "",
                "source_lemma": source_lemma.strip() if lemma_sep else "",
                "dictionary_gloss": clean_context_gloss(dictionary_gloss) if lemma_sep else "",
                "editions": editions,
            }
            key = f"{int(match.group(2))}:{int(match.group(3))}"
            books[book_id][key].append(row)
            token_count += 1
    output: dict[str, dict] = {}
    missing = []
    for book_id, verses in books.items():
        if not verses:
            missing.append(book_id)
            continue
        output[book_id] = {
            "schema_version": 1,
            "book_id": book_id,
            "language": "grc",
            "source": "STEPBible TAGNT",
            "relationship": (
                "contextual semantic aid only; attach to SBLGNT tokens only after preserved-surface verification; "
                "not a replacement for MorphGNT or SBLGNT"
            ),
            "verses": {
                key: sorted(rows, key=lambda row: row["source_position"])
                for key, rows in sorted(verses.items())
            },
        }
    if missing:
        raise BuildError(f"TAGNT context missing NT books: {missing}")
    return output, token_count


def parse_tahot(texts: list[str]) -> tuple[dict[str, dict], int]:
    books: dict[str, dict[str, list[dict]]] = {book_id: defaultdict(list) for book_id in OT_BOOKS.values()}
    token_count = 0
    for text in texts:
        for raw in text.splitlines():
            if not raw or raw.startswith("#"):
                continue
            parts = raw.rstrip("\n").split("\t")
            if len(parts) < 6:
                continue
            match = TAHOT_REF_RE.fullmatch(parts[0].strip())
            if not match:
                continue
            book_id = OT_BOOKS.get(match.group(1))
            if not book_id:
                continue
            text_type = match.group(5)
            if not text_type or text_type[0] not in {"L", "Q", "R", "X"}:
                continue
            strong_field = parts[4].strip()
            root_match = re.search(r"\{(H\d{4,5}[A-Z]?)\}", strong_field)
            root_strong = root_match.group(1) if root_match else first_strong(strong_field)
            row = {
                "source_position": int(match.group(4)),
                "text_type": text_type,
                "surface": parts[1].strip(),
                "transliteration": parts[2].strip(),
                "contextual_gloss": clean_context_gloss(parts[3]),
                "root_strong": root_strong,
                "strong_tags": all_strongs(strong_field),
                "morphology_code": parts[5].strip(),
            }
            key = f"{int(match.group(2))}:{int(match.group(3))}"
            books[book_id][key].append(row)
            token_count += 1
    output: dict[str, dict] = {}
    missing = []
    for book_id, verses in books.items():
        if not verses:
            missing.append(book_id)
            continue
        output[book_id] = {
            "schema_version": 1,
            "book_id": book_id,
            "languages": ["he", "arc"],
            "source": "STEPBible TAHOT",
            "relationship": (
                "contextual semantic aid only; attach to OSHB/WLC tokens only after preserved-surface verification"
            ),
            "verses": {
                key: sorted(rows, key=lambda row: row["source_position"])
                for key, rows in sorted(verses.items())
            },
        }
    if missing:
        raise BuildError(f"TAHOT context missing Masoretic books: {missing}")
    return output, token_count


def greek_ot_lexical_audit(greek_lexicon: dict, catholic_ot_ids: list[str]) -> dict:
    lemma_index = greek_lexicon["lemma_index"]
    books = []
    total_tokens = matched = proper_names = 0
    for book_id in catholic_ot_ids:
        path = RAHLFS_ROOT / f"{book_id}.json"
        if not path.exists():
            raise BuildError(f"Rahlfs linguistic witness missing for {book_id}")
        payload = load_json(path)
        book_total = book_matched = book_names = 0
        for verse in payload.get("verses") or []:
            for token in verse.get("tokens") or []:
                book_total += 1
                pos = str(token.get("part_of_speech") or "").lower()
                if "proper" in pos:
                    book_names += 1
                    continue
                key = normalize_greek(str(token.get("lemma") or ""))
                if key and lemma_index.get(key):
                    book_matched += 1
        total_tokens += book_total
        matched += book_matched
        proper_names += book_names
        eligible = max(1, book_total - book_names)
        books.append({
            "book_id": book_id,
            "token_count": book_total,
            "proper_name_token_count": book_names,
            "lexicon_matched_non_name_tokens": book_matched,
            "non_name_match_ratio": round(book_matched / eligible, 6),
        })
    eligible_total = max(1, total_tokens - proper_names)
    return {
        "book_count": len(books),
        "token_count": total_tokens,
        "proper_name_token_count": proper_names,
        "lexicon_matched_non_name_tokens": matched,
        "non_name_match_ratio": round(matched / eligible_total, 6),
        "books": books,
    }


def build(output: Path, *, production: bool) -> dict:
    lock = load_json(LOCK_PATH)
    if lock.get("corpus_id") != "logos_stepbible_semantics":
        raise BuildError("unexpected semantic source lock corpus id")
    upstream = lock.get("upstream") or {}
    repo = str(upstream.get("repository") or "")
    commit = str(upstream.get("commit") or "")
    files = lock.get("files") or {}

    downloaded: dict[str, str] = {}
    sha256s: dict[str, str] = {}
    for source_id, meta in files.items():
        text, sha256 = download_pinned(repo, commit, meta["path"], meta["blob_sha1"])
        downloaded[source_id] = text
        sha256s[source_id] = sha256

    greek_lexicon = parse_greek_lexicon(downloaded["tbesg"])
    hebrew_lexicon = parse_hebrew_lexicon(downloaded["tbesh"])
    greek_morph = parse_morphology(downloaded["tegmc"], "grc")
    hebrew_morph = parse_morphology(downloaded["tehmc"], "he-arc")
    nt_context, nt_context_tokens = parse_tagnt([
        downloaded["tagnt_mat_jhn"],
        downloaded["tagnt_act_rev"],
    ])
    ot_context, ot_context_tokens = parse_tahot([
        downloaded["tahot_gen_deu"],
        downloaded["tahot_jos_est"],
        downloaded["tahot_job_sng"],
        downloaded["tahot_isa_mal"],
    ])

    books = load_json(BOOKS_PATH).get("books") or []
    if len(books) != 73:
        raise BuildError(f"canonical book inventory changed: {len(books)}")
    nt_ids = [str(row["id"]) for row in books if row.get("testament") == "NT"]
    ot_ids = [str(row["id"]) for row in books if row.get("testament") == "OT"]
    if set(nt_ids) != set(NT_BOOKS.values()) or len(nt_ids) != 27:
        raise BuildError("semantic NT book map must cover exactly 27 canonical NT books")
    if len(ot_ids) != 46:
        raise BuildError("semantic OT coverage requires exactly 46 Catholic OT books")
    if set(OT_BOOKS.values()) - set(ot_ids):
        raise BuildError("TAHOT Masoretic map includes a non-canonical/missing OT book")

    greek_ot_audit = greek_ot_lexical_audit(greek_lexicon, ot_ids)

    if output.exists():
        shutil.rmtree(output)
    write_json(output / "lexicon" / "greek.json", greek_lexicon)
    write_json(output / "lexicon" / "hebrew.json", hebrew_lexicon)
    write_json(output / "morphology" / "greek.json", greek_morph)
    write_json(output / "morphology" / "hebrew.json", hebrew_morph)
    for book_id, payload in nt_context.items():
        write_json(output / "context" / "nt" / f"{book_id}.json", payload)
    for book_id, payload in ot_context.items():
        write_json(output / "context" / "ot-semitic" / f"{book_id}.json", payload)

    semantic_books = []
    for row in books:
        book_id = str(row["id"])
        testament = str(row.get("testament"))
        lanes = []
        if testament == "NT":
            lanes.append("greek-nt-contextual")
        else:
            lanes.append("greek-ot-rahlfs-lexical")
            if book_id in OT_BOOKS.values():
                lanes.insert(0, "hebrew-aramaic-contextual")
        semantic_books.append({
            "order": row.get("order"),
            "book_id": book_id,
            "book": row.get("name"),
            "testament": testament,
            "semantic_lanes": lanes,
        })

    manifest = {
        "schema_version": 1,
        "corpus_id": "logos_stepbible_semantics",
        "corpus_version": f"2026.09.23-{commit[:7]}-{'production' if production else 'validation'}",
        "status": "production-installed" if production else "validation-only",
        "production_enabled": production,
        "scope": (
            "Semantic/lexical support for all 73 Catholic books: contextual Greek NT, contextual Hebrew/Aramaic "
            "where Masoretic witnesses exist, and a separate Rahlfs Greek OT lexical/grammar witness for all 46 OT books."
        ),
        "source": {
            "repository": repo,
            "commit": commit,
            "license": upstream.get("license"),
            "attribution": upstream.get("attribution"),
            "files": {
                source_id: {
                    "path": files[source_id]["path"],
                    "blob_sha1": files[source_id]["blob_sha1"],
                    "sha256": sha256s[source_id],
                }
                for source_id in sorted(files)
            },
        },
        "rights_policy": lock.get("rights_policy") or {},
        "coverage": {
            "catholic_book_count": 73,
            "nt_context_book_count": len(nt_context),
            "hebrew_aramaic_context_book_count": len(ot_context),
            "greek_ot_rahlfs_book_count": greek_ot_audit["book_count"],
            "semantic_book_coverage": len(semantic_books),
            "greek_lexicon_entry_count": len(greek_lexicon["entries"]),
            "hebrew_lexicon_entry_count": len(hebrew_lexicon["entries"]),
            "greek_morphology_code_count": len(greek_morph["records"]),
            "hebrew_morphology_code_count": len(hebrew_morph["records"]),
            "nt_context_token_count": nt_context_tokens,
            "hebrew_aramaic_context_token_count": ot_context_tokens,
            "greek_ot_non_name_lexicon_match_ratio": greek_ot_audit["non_name_match_ratio"],
        },
        "greek_ot_lexical_audit": greek_ot_audit,
        "books": semantic_books,
        "runtime_contract": {
            "english_primary_text": "Douay-Rheims 1899",
            "tagnt_attaches_only_after_surface_verification": True,
            "tahot_attaches_only_after_surface_verification": True,
            "rahlfs_remains_separate_from_swete": True,
            "rahlfs_canonical_verse_identity_not_implied": True,
            "hebrew_restricted_meaning_field_excluded": True,
            "no_fabricated_contextual_meaning": True,
            "contextual_gloss_is_not_douay_token_alignment": True,
        },
    }
    write_json(output / "manifest.json", manifest, pretty=True)
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument("--production", action="store_true")
    args = parser.parse_args()
    output = (args.output or (PRODUCTION_OUTPUT if args.production else DEFAULT_OUTPUT)).resolve()
    manifest = build(output, production=args.production)
    coverage = manifest["coverage"]
    print(
        "Semantic interlinear corpus built: "
        f"{coverage['semantic_book_coverage']}/73 books; "
        f"NT contextual={coverage['nt_context_book_count']}; "
        f"Hebrew/Aramaic contextual={coverage['hebrew_aramaic_context_book_count']}; "
        f"Greek OT Rahlfs lexical={coverage['greek_ot_rahlfs_book_count']}; "
        f"Greek OT non-name lexicon match={coverage['greek_ot_non_name_lexicon_match_ratio']:.2%}; "
        f"production={manifest['production_enabled']}"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        raise SystemExit(f"Semantic interlinear build failed: {exc}") from exc
