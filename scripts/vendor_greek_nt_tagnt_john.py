#!/usr/bin/env python3
"""Vendor TAGNT word-level linguistic evidence for the MorphGNT John 7:53–8:11 gap.

TAGNT is kept as a supplemental, amalgamated Greek witness. The importer never
claims TAGNT tokens are MorphGNT annotations or that they are token-identical to
SBLGNT. Edition membership and variant metadata remain visible per source row.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_nt_tagnt_john_pa"
REPOSITORY = "STEPBible/STEPBible-Data"
COMMIT = "ae39711d7843b2902d54993e432de9c12d6a4b9a"
PATH = "Translators Amalgamated OT+NT/TAGNT Mat-Jhn - Translators Amalgamated Greek NT - STEPBible.org CC-BY.txt"
GIT_BLOB_SHA1 = "705c1bc1cf752e013efcef99b8d9a3b7853bf843"
CORPUS_ID = "grc_nt_tagnt_john_pa"
CORPUS_VERSION = "2026.09.22-tagnt-john-pa-v1"
TARGET_REFS = ["7:53"] + [f"8:{i}" for i in range(1, 12)]
ROW_RE = re.compile(r"^Jhn\.(7\.53(?:\{8\.1\})?|8\.(?:1|2|3|4|5|6|7|8|9|10|11))#(\d+)=([^\t]+)\t")
POS_RE = re.compile(r"=([A-Z][A-Z0-9]*(?:-[A-Z0-9]+)*)")
DICT_RE = re.compile(r"(?:^|\+\s*)([^=+]+)=")


class BuildError(RuntimeError):
    pass


def git_blob_sha1(payload: bytes) -> str:
    return hashlib.sha1(f"blob {len(payload)}\0".encode("ascii") + payload).hexdigest()


def download() -> bytes:
    url = f"https://raw.githubusercontent.com/{REPOSITORY}/{COMMIT}/{quote(PATH, safe='/')}"
    request = Request(url, headers={"User-Agent": "Mercy-Logos-TAGNT-John/1.0"})
    last_error: Exception | None = None
    for attempt in range(3):
        try:
            with urlopen(request, timeout=90) as response:
                payload = response.read()
            actual = git_blob_sha1(payload)
            if actual != GIT_BLOB_SHA1:
                raise BuildError(f"TAGNT Git blob mismatch: expected {GIT_BLOB_SHA1}, got {actual}")
            return payload
        except (HTTPError, URLError, TimeoutError) as exc:
            last_error = exc
            if attempt < 2:
                time.sleep(2**attempt)
    raise BuildError(f"cannot download pinned TAGNT file: {last_error}")


def clean_surface(value: str) -> str:
    value = value.strip()
    if " (" in value and value.endswith(")"):
        value = value.rsplit(" (", 1)[0].strip()
    return value


def dictionary_forms(raw: str) -> list[str]:
    values = []
    for match in DICT_RE.finditer(raw):
        value = match.group(1).strip()
        if value and value not in values:
            values.append(value)
    return values


def parse(payload: bytes) -> dict[str, list[dict]]:
    try:
        text = payload.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise BuildError(f"TAGNT is not UTF-8: {exc}") from exc
    if "STEPBible.org CC BY 4.0" not in text[:1000]:
        raise BuildError("TAGNT CC BY 4.0 header changed")
    if "All the words from standard Greek editions" not in text[:5000]:
        raise BuildError("TAGNT edition-amalgamation header changed")

    grouped = {ref: [] for ref in TARGET_REFS}
    for line in text.splitlines():
        match = ROW_RE.match(line)
        if not match:
            continue
        raw_locus, position, word_type = match.groups()
        source_ref = raw_locus.replace("{8.1}", "").replace(".", ":")
        if source_ref not in grouped:
            continue
        cols = line.split("\t")
        if len(cols) < 6:
            raise BuildError(f"TAGNT {source_ref} row has fewer than six columns")
        greek_raw = cols[1].strip()
        grammar = cols[3].strip()
        dictionary = cols[4].strip()
        editions = cols[5].strip()
        surface = clean_surface(greek_raw)
        if not surface or not grammar or not dictionary:
            raise BuildError(f"TAGNT {source_ref} token {position}: required linguistic fields are empty")
        grammar_codes = POS_RE.findall(grammar)
        pos_codes = []
        for code in grammar_codes:
            pos = code.split("-", 1)[0]
            if pos and pos not in pos_codes:
                pos_codes.append(pos)
        grouped[source_ref].append(
            {
                "position": int(position),
                "raw_reference": cols[0].strip(),
                "word_type": word_type.strip(),
                "surface": surface,
                "greek_raw": greek_raw,
                "dstrongs_grammar": grammar,
                "part_of_speech_codes": pos_codes,
                "dictionary_raw": dictionary,
                "dictionary_forms": dictionary_forms(dictionary),
                "editions": editions,
                "english_translation": cols[2].strip(),
                "meaning_variants": cols[6].strip() if len(cols) > 6 else "",
                "spelling_variants": cols[7].strip() if len(cols) > 7 else "",
                "sstrong_instance": cols[11].strip() if len(cols) > 11 else "",
                "alt_strongs": cols[12].strip() if len(cols) > 12 else "",
            }
        )
    missing = [ref for ref, rows in grouped.items() if not rows]
    if missing:
        raise BuildError(f"TAGNT missing target John verses: {missing}")
    for ref, rows in grouped.items():
        positions = [int(row["position"]) for row in rows]
        if len(positions) != len(set(positions)):
            raise BuildError(f"TAGNT {ref}: duplicate token positions")
        rows.sort(key=lambda row: int(row["position"]))
    return grouped


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def build(output: Path) -> dict:
    payload = download()
    grouped = parse(payload)
    if output.exists():
        import shutil
        shutil.rmtree(output)
    output.mkdir(parents=True, exist_ok=True)

    verses = [
        {
            "reference": ref,
            "canonical_reference": f"John {ref}",
            "tokens": grouped[ref],
            "token_count": len(grouped[ref]),
        }
        for ref in TARGET_REFS
    ]
    token_count = sum(row["token_count"] for row in verses)
    manifest = {
        "schema_version": 1,
        "corpus_id": CORPUS_ID,
        "corpus_version": CORPUS_VERSION,
        "status": "production-installed",
        "production_enabled": True,
        "language": "grc",
        "book_id": "JHN",
        "book": "John",
        "scope": "Supplemental TAGNT linguistic witness for the 12 verses absent from pinned MorphGNT: John 7:53 and 8:1-11.",
        "verse_count": 12,
        "token_count": token_count,
        "source": {
            "source_id": "stepbible-data",
            "dataset": "TAGNT",
            "repository": REPOSITORY,
            "commit": COMMIT,
            "path": PATH,
            "git_blob_sha1": GIT_BLOB_SHA1,
            "sha256": hashlib.sha256(payload).hexdigest(),
            "license": "CC BY 4.0",
            "attribution": "STEP Bible — https://www.STEPBible.org",
        },
        "witness_policy": {
            "relationship_to_sblgnt": "supplemental-parallel-linguistic-witness",
            "automatic_attachment_to_sblgnt": False,
            "automatic_reconstruction_of_sblgnt": False,
            "tagnt_is_amalgamated": True,
            "edition_membership_preserved_per_token": True,
            "word_type_preserved_per_token": True,
            "variant_fields_preserved_per_token": True,
            "no_fabricated_pos_labels": True,
            "no_fabricated_lemma": True,
            "no_fabricated_morphology": True,
        },
        "field_contract": {
            "surface": "TAGNT Greek column, transliteration display suffix removed only for the convenience surface field; greek_raw remains preserved",
            "lemma": "TAGNT Dictionary form field preserved as dictionary_raw/dictionary_forms",
            "part_of_speech": "TAGNT source grammar codes preserved as part_of_speech_codes; no normalized POS label invented",
            "morphology": "TAGNT dStrongs = Grammar field preserved verbatim",
            "edition_membership": "TAGNT editions field preserved verbatim",
        },
        "verses": verses,
        "note": "This package completes linguistic analysis availability for the MorphGNT-locked passage gap without representing TAGNT as MorphGNT or claiming token identity with SBLGNT.",
    }
    write_json(output / "manifest.json", manifest)
    print(f"TAGNT John supplement built: 12 verses / {token_count} source token rows")
    return manifest


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    build(args.output.resolve())
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except BuildError as exc:
        raise SystemExit(f"TAGNT John supplement build failed: {exc}") from exc
