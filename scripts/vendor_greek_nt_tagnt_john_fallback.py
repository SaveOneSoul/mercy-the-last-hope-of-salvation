#!/usr/bin/env python3
"""Vendor the source-locked TAGNT linguistic witness for John 7:53-8:11.

This is a supplemental source layer only. It does not rewrite SBLGNT surface
tokens or MorphGNT annotations, and it does not claim one-to-one token identity
across editions.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
from collections import defaultdict
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
LOCK = ROOT / "cloud-backend/app/logos_interlinear/greek_nt_linguistics_phase2a/source-lock.json"
DEFAULT_OUTPUT = ROOT / "cloud-backend/app/logos_corpus/grc_tagnt_john_fallback"
ROW_RE = re.compile(r"^Jhn\.(7\.53(?:\{8\.1\})?|8\.(?:[1-9]|10|11))#(\d+)=([^\t]+)\t")
GREEK_WITH_TRANSLIT_RE = re.compile(r"^(.*?)\s*\(([^()]*)\)\s*$")


class BuildError(RuntimeError):
    pass


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def download(lock: dict) -> tuple[str, str]:
    source = lock["source"]
    path = quote(source["path"], safe="/")
    url = f"https://raw.githubusercontent.com/{source['repository']}/{source['commit']}/{path}"
    req = Request(url, headers={"User-Agent": "Mercy-Logos-TAGNT-Phase2A/1.0"})
    with urlopen(req, timeout=90) as response:
        payload = response.read()
    actual = git_blob_sha1(payload)
    if actual != source["blob_sha1"]:
        raise BuildError(f"TAGNT blob mismatch: expected {source['blob_sha1']}, got {actual}")
    return payload.decode("utf-8-sig"), hashlib.sha256(payload).hexdigest()


def source_ref(raw: str) -> str:
    raw = raw.replace("{8.1}", "")
    chapter, verse = raw.split(".", 1)
    return f"{chapter}:{verse}"


def split_greek(value: str) -> tuple[str, str | None]:
    value = value.strip()
    match = GREEK_WITH_TRANSLIT_RE.match(value)
    if match:
        return match.group(1).strip(), match.group(2).strip() or None
    return value, None


def parse(text: str, expected_refs: list[str]) -> dict[str, list[dict]]:
    expected = set(expected_refs)
    verses: dict[str, list[dict]] = defaultdict(list)
    for line_no, raw in enumerate(text.splitlines(), start=1):
        match = ROW_RE.match(raw)
        if not match:
            continue
        ref = source_ref(match.group(1))
        if ref not in expected:
            continue
        cols = raw.split("\t")
        if len(cols) < 6:
            raise BuildError(f"TAGNT line {line_no}: too few columns")
        row_ref = cols[0]
        position = int(match.group(2))
        word_type = match.group(3)
        surface, transliteration = split_greek(cols[1])
        english = cols[2].strip()
        grammar = cols[3].strip()
        dictionary = cols[4].strip()
        editions = cols[5].strip()
        if not surface or not grammar or "=" not in grammar or not dictionary:
            raise BuildError(f"TAGNT {row_ref}: missing surface/grammar/dictionary data")
        strongs, morphology = grammar.split("=", 1)
        lemma, _, lexical_gloss = dictionary.partition("=")
        if not strongs.strip() or not morphology.strip() or not lemma.strip():
            raise BuildError(f"TAGNT {row_ref}: incomplete linguistic fields")
        verses[ref].append({
            "source_token_ref": row_ref,
            "position": position,
            "word_type": word_type,
            "surface": surface,
            "transliteration": transliteration,
            "english_translation": english,
            "strongs": strongs.strip(),
            "part_of_speech_morphology": morphology.strip(),
            "lemma": lemma.strip(),
            "lexical_gloss": lexical_gloss.strip() or None,
            "editions": editions,
            "meaning_variants": cols[6].strip() if len(cols) > 6 else "",
            "spelling_variants": cols[7].strip() if len(cols) > 7 else "",
        })
    missing = expected - set(verses)
    extra = set(verses) - expected
    if missing or extra:
        raise BuildError(f"TAGNT reference inventory mismatch: missing={sorted(missing)}, extra={sorted(extra)}")
    for ref, rows in verses.items():
        positions = [r["position"] for r in rows]
        if positions != list(range(1, len(rows) + 1)):
            raise BuildError(f"TAGNT {ref}: token positions are not contiguous: {positions}")
    return dict(verses)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    lock = load(LOCK)
    expected_refs = list(lock["coverage"]["references"])
    text, sha256 = download(lock)
    verses = parse(text, expected_refs)
    token_count = sum(len(rows) for rows in verses.values())
    if token_count != int(lock["coverage"]["expected_token_rows"]):
        raise BuildError(f"TAGNT token-row count changed: expected {lock['coverage']['expected_token_rows']}, got {token_count}")

    source = dict(lock["source"])
    source["sha256"] = sha256
    payload = {
        "schema_version": 1,
        "corpus_id": "grc_tagnt_john_fallback",
        "corpus_version": "2026.09.22-tagnt-john-phase2a",
        "status": "production-installed",
        "production_enabled": True,
        "language": "grc",
        "scope": "John 7:53-8:11 supplemental linguistic witness",
        "book_id": "JHN",
        "source": source,
        "coverage": {
            "reference_count": len(expected_refs),
            "references": expected_refs,
            "token_row_count": token_count,
            "lemma_morphology_complete": True,
        },
        "alignment_policy": {
            "source_tokenization_preserved": True,
            "cross_edition_token_identity_claimed": False,
            "sblgnt_surface_overwritten": False,
            "morphgnt_overwritten": False,
            "note": "TAGNT is served/audited as a separate linguistic witness for the MorphGNT gap.",
        },
        "field_provenance": {
            "surface": "TAGNT Greek column",
            "transliteration": "TAGNT Greek column parenthetical",
            "english_translation": "TAGNT English translation column",
            "strongs": "TAGNT dStrongs=Grammar column",
            "part_of_speech_morphology": "TAGNT dStrongs=Grammar column",
            "lemma": "TAGNT Dictionary form=Gloss column",
            "lexical_gloss": "TAGNT Dictionary form=Gloss column",
            "editions": "TAGNT editions column",
            "meaning_variants": "TAGNT meaning variants column",
            "spelling_variants": "TAGNT spelling variants column",
        },
        "verses": verses,
    }
    out = args.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    (out / "JHN-7-53--8-11.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out / "manifest.json").write_text(json.dumps({
        "schema_version": 1,
        "corpus_id": payload["corpus_id"],
        "corpus_version": payload["corpus_version"],
        "status": payload["status"],
        "production_enabled": True,
        "book_count": 1,
        "verse_count": len(expected_refs),
        "token_row_count": token_count,
        "references": expected_refs,
        "source": source,
        "cross_edition_token_identity_claimed": False,
        "no_fabricated_linguistics": True,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"[TAGNT Phase 2A] vendored {len(expected_refs)} John verses / {token_count} source linguistic rows")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (BuildError, OSError, ValueError, json.JSONDecodeError) as exc:
        raise SystemExit(f"TAGNT John fallback build failed: {exc}") from exc
