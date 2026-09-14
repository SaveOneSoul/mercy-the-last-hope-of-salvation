#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "cloud-backend" / "app" / "logos_interlinear"
PROTO_DIR = BASE / "prototypes" / "john-1-1"
DATA_PATH = PROTO_DIR / "JHN-1-1.json"
SOURCES_PATH = PROTO_DIR / "sources-manifest.json"
TOKEN_SCHEMA_PATH = BASE / "token.schema.json"
PAGE_PATH = ROOT / "pages" / "logos-interlinear-v1.html"
JS_PATH = ROOT / "javascript" / "logos-interlinear-v1.js"
CSS_PATH = ROOT / "css" / "logos-interlinear-v1.css"
PAGES_WORKFLOW = ROOT / ".github" / "workflows" / "mercy-pages.yml"

SBL_COMMIT = "c4d241a9c1c479a55b989ba35a4976c1d0b8052c"
SBL_BLOB = "a79ae036447d48fd88c4db8e166c771b4fc57d93"
MORPH_COMMIT = "aaed91e57c8e4a8dc9a2383e129ca5e75fe6393d"
MORPH_BLOB = "c3dab42934edab531f7dc08b630be8181638bd61"
EXPECTED_TEXT = "Ἐν ἀρχῇ ἦν ὁ λόγος, καὶ ὁ λόγος ἦν πρὸς τὸν θεόν, καὶ θεὸς ἦν ὁ λόγος."
EXPECTED = [
    ("Ἐν", "ἐν", "preposition", "--------"),
    ("ἀρχῇ", "ἀρχή", "noun", "----DSF-"),
    ("ἦν", "εἰμί", "verb", "3IAI-S--"),
    ("ὁ", "ὁ", "article", "----NSM-"),
    ("λόγος,", "λόγος", "noun", "----NSM-"),
    ("καὶ", "καί", "conjunction", "--------"),
    ("ὁ", "ὁ", "article", "----NSM-"),
    ("λόγος", "λόγος", "noun", "----NSM-"),
    ("ἦν", "εἰμί", "verb", "3IAI-S--"),
    ("πρὸς", "πρός", "preposition", "--------"),
    ("τὸν", "ὁ", "article", "----ASM-"),
    ("θεόν,", "θεός", "noun", "----ASM-"),
    ("καὶ", "καί", "conjunction", "--------"),
    ("θεὸς", "θεός", "noun", "----NSM-"),
    ("ἦν", "εἰμί", "verb", "3IAI-S--"),
    ("ὁ", "ὁ", "article", "----NSM-"),
    ("λόγος.", "λόγος", "noun", "----NSM-"),
]


def fail(message: str) -> None:
    raise SystemExit(f"Logos John 1:1 prototype validation failed: {message}")


def load(path: Path) -> dict:
    if not path.exists():
        fail(f"missing {path.relative_to(ROOT)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot parse {path.relative_to(ROOT)}: {exc}")


def main() -> int:
    data = load(DATA_PATH)
    sources = load(SOURCES_PATH)
    schema = load(TOKEN_SCHEMA_PATH)

    if data.get("reference") != "John 1:1" or data.get("book_id") != "JHN":
        fail("prototype must remain scoped to John 1:1")
    if data.get("language") != "grc" or data.get("greek_text") != EXPECTED_TEXT:
        fail("Greek source text does not match the pinned John 1:1 gate")
    if data.get("scale_gate", {}).get("full_nt_scaling_allowed") is not False:
        fail("27-book scaling must remain locked during the prototype milestone")

    source_index = {row["id"]: row for row in sources.get("sources", [])}
    if set(source_index) != {"sblgnt", "morphgnt-sblgnt"}:
        fail("prototype source manifest must contain exactly SBLGNT and MorphGNT")

    sbl = source_index["sblgnt"]
    if sbl.get("commit") != SBL_COMMIT or sbl.get("blob_sha1") != SBL_BLOB:
        fail("SBLGNT immutable source pin changed")
    if sbl.get("license") != "CC BY 4.0" or sbl.get("license_verified") is not True:
        fail("SBLGNT licence gate is not satisfied")
    if sbl.get("verified_text") != EXPECTED_TEXT:
        fail("source manifest SBLGNT John 1:1 text mismatch")

    morph = source_index["morphgnt-sblgnt"]
    if morph.get("commit") != MORPH_COMMIT or morph.get("blob_sha1") != MORPH_BLOB:
        fail("MorphGNT immutable source pin changed")
    if "CC BY-SA 3.0" not in str(morph.get("license")):
        fail("MorphGNT annotation licence must remain CC BY-SA 3.0")
    if morph.get("share_alike") is not True or morph.get("isolation_required") is not True:
        fail("MorphGNT ShareAlike isolation gate is missing")
    if morph.get("prototype_import_allowed") is not True:
        fail("MorphGNT is not approved for this one-verse prototype")
    if morph.get("bulk_production_import_allowed") is not False:
        fail("full-NT MorphGNT bulk import must remain blocked at this milestone")

    required = set(schema.get("required") or [])
    tokens = data.get("tokens") or []
    if len(tokens) != 17 or data.get("token_count") != 17:
        fail(f"expected exactly 17 tokens, found {len(tokens)}")
    if [row.get("position") for row in tokens] != list(range(1, 18)):
        fail("token positions must be contiguous 1..17")

    for index, (token, expected) in enumerate(zip(tokens, EXPECTED), start=1):
        missing = sorted(required - set(token))
        if missing:
            fail(f"token {index} missing required fields: {', '.join(missing)}")
        surface, lemma, part_of_speech, morphology = expected
        if token.get("surface") != surface:
            fail(f"token {index} SBLGNT surface mismatch")
        if token.get("lemma") != lemma:
            fail(f"token {index} MorphGNT lemma mismatch")
        if token.get("part_of_speech") != part_of_speech:
            fail(f"token {index} part-of-speech mapping mismatch")
        if token.get("morphology") != morphology:
            fail(f"token {index} MorphGNT morphology mismatch")
        if token.get("text_source") != "sblgnt":
            fail(f"token {index} must identify SBLGNT as text source")
        if token.get("linguistic_source") != "morphgnt-sblgnt":
            fail(f"token {index} must identify MorphGNT as linguistic source")
        if token.get("source_revision") != MORPH_COMMIT:
            fail(f"token {index} must retain the MorphGNT revision")
        if not token.get("transliteration") or not token.get("gloss"):
            fail(f"token {index} lacks derived transliteration or study gloss")

    recomposed = " ".join(row["surface"] for row in tokens)
    if recomposed != EXPECTED_TEXT:
        fail("word-token surfaces do not recompose to exact SBLGNT John 1:1")

    provenance = data.get("field_provenance") or {}
    if provenance.get("surface", {}).get("source") != "sblgnt":
        fail("surface field provenance is missing")
    if provenance.get("lemma", {}).get("source") != "morphgnt-sblgnt":
        fail("lemma field provenance is missing")
    if provenance.get("transliteration", {}).get("source") != "logos-derived-greek-transliteration-v1":
        fail("transliteration derivation is not identified")
    if provenance.get("gloss", {}).get("source") != "logos-curated-gloss-v1":
        fail("gloss provenance is not identified")

    for path in (PAGE_PATH, JS_PATH, CSS_PATH, PAGES_WORKFLOW):
        if not path.exists():
            fail(f"rendering file missing: {path.relative_to(ROOT)}")

    js = JS_PATH.read_text(encoding="utf-8")
    if "../data/logos-interlinear/JHN-1-1.json" not in js:
        fail("renderer is not wired to the published prototype JSON")
    workflow = PAGES_WORKFLOW.read_text(encoding="utf-8")
    if "data/logos-interlinear" not in workflow or "JHN-1-1.json" not in workflow:
        fail("GitHub Pages workflow does not publish the prototype JSON")

    print(
        "Logos John 1:1 prototype validation passed: "
        "2 source pins, 17 Greek tokens, provenance gate, ShareAlike isolation, and static renderer wiring verified"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
