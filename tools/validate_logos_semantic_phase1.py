#!/usr/bin/env python3
"""Validate the source-locked 73-book Logos semantic interlinear corpus."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOCK_PATH = ROOT / "cloud-backend" / "app" / "logos_interlinear" / "semantic_phase1" / "source-lock.json"
DEFAULT_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "semantic_stepbible"

EXPECTED_COMMIT = "b99716b0cddb648ddb95cc786a197180f2f97d48"
EXPECTED_BLOBS = {
    "tbesg": "efe271a1dbb73fa01f8fa6e0f164c6687757a9ae",
    "tbesh": "a64990a674d13245ae1e9ed426bc69197c2fbad5",
    "tegmc": "314ac3d791df69c0736b1df8aabca7ac0956b1e1",
    "tehmc": "fa08a680ed8084e8041bdfd6e6ac6d93a00f2efb",
    "tagnt_mat_jhn": "705c1bc1cf752e013efcef99b8d9a3b7853bf843",
    "tagnt_act_rev": "4bbea2c14681b01eb889d5a2d1dc0856858a32de",
    "tahot_gen_deu": "eb051292f8cee648c4f3eaf1b48cd0f1f30dc1d5",
    "tahot_jos_est": "e3824344f6dea1a3f51932d1b0a53537c3c2023e",
    "tahot_job_sng": "3d7af689417b54ebc468700b2bd86a8ba5377530",
    "tahot_isa_mal": "1cfe6718a1dae0d5d45a57a942d3f7f716ac6342",
}


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def require(condition: bool, message: str) -> None:
    if not condition:
        raise SystemExit(message)


def lexicon_entry(payload: dict, strong: str) -> dict:
    ids = payload.get("strong_index", {}).get(strong) or []
    require(bool(ids), f"lexicon alias missing: {strong}")
    return payload["entries"][int(ids[0])]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--require-production", action="store_true")
    args = parser.parse_args()
    root = args.root.resolve()

    lock = load(LOCK_PATH)
    require(lock.get("corpus_id") == "logos_stepbible_semantics", "semantic source-lock corpus id changed")
    require((lock.get("upstream") or {}).get("commit") == EXPECTED_COMMIT, "STEPBible semantic source pin changed")
    require((lock.get("upstream") or {}).get("license") == "CC BY 4.0", "STEPBible semantic license changed")
    files = lock.get("files") or {}
    for source_id, blob in EXPECTED_BLOBS.items():
        require((files.get(source_id) or {}).get("blob_sha1") == blob, f"semantic source blob changed: {source_id}")

    rights = lock.get("rights_policy") or {}
    require(rights.get("include_hebrew_tbesh_meaning") is False, "restricted TBESH Meaning field must stay excluded")
    require(rights.get("no_cross_edition_attachment") is True, "cross-edition semantic safety gate changed")
    require(rights.get("no_fabricated_contextual_meaning") is True, "semantic no-fabrication gate changed")

    manifest = load(root / "manifest.json")
    require(manifest.get("corpus_id") == "logos_stepbible_semantics", "unexpected semantic corpus id")
    if args.require_production:
        require(manifest.get("production_enabled") is True, "semantic corpus is not production-enabled")
        require(manifest.get("status") == "production-installed", "semantic corpus is not production-installed")

    coverage = manifest.get("coverage") or {}
    require(int(coverage.get("catholic_book_count") or 0) == 73, "semantic canonical count must be 73")
    require(int(coverage.get("semantic_book_coverage") or 0) == 73, "semantic coverage must be 73/73 books")
    require(int(coverage.get("nt_context_book_count") or 0) == 27, "NT semantic context must cover 27 books")
    require(int(coverage.get("hebrew_aramaic_context_book_count") or 0) == 39, "Semitic semantic context must cover 39 books")
    require(int(coverage.get("greek_ot_rahlfs_book_count") or 0) == 46, "Rahlfs semantic witness must cover 46 OT books")
    require(int(coverage.get("greek_lexicon_entry_count") or 0) >= 10000, "Greek lexicon unexpectedly small")
    require(int(coverage.get("hebrew_lexicon_entry_count") or 0) >= 8000, "Hebrew lexicon unexpectedly small")
    require(int(coverage.get("greek_morphology_code_count") or 0) >= 100, "Greek morphology expansion table unexpectedly small")
    require(int(coverage.get("hebrew_morphology_code_count") or 0) >= 100, "Hebrew morphology expansion table unexpectedly small")
    require(float(coverage.get("greek_ot_non_name_lexicon_match_ratio") or 0) >= 0.80, "Greek OT lexical match ratio fell below 80%")

    books = manifest.get("books") or []
    require(len(books) == 73, "semantic manifest must list 73 books")
    require(len({row.get("book_id") for row in books}) == 73, "semantic manifest book ids are not unique")
    nt = [row for row in books if row.get("testament") == "NT"]
    ot = [row for row in books if row.get("testament") == "OT"]
    require(len(nt) == 27 and all("greek-nt-contextual" in row.get("semantic_lanes", []) for row in nt), "NT semantic lane coverage changed")
    require(len(ot) == 46 and all("greek-ot-rahlfs-lexical" in row.get("semantic_lanes", []) for row in ot), "OT Greek semantic lane coverage changed")

    greek = load(root / "lexicon" / "greek.json")
    hebrew = load(root / "lexicon" / "hebrew.json")
    greek_morph = load(root / "morphology" / "greek.json")
    hebrew_morph = load(root / "morphology" / "hebrew.json")

    logos = lexicon_entry(greek, "G3056")
    require(logos.get("gloss") == "word", "G3056 Logos gloss changed")
    require("Word" in str(logos.get("meaning") or "") or "word" in str(logos.get("meaning") or "").lower(), "G3056 lexical meaning missing")
    theos = lexicon_entry(greek, "G2316")
    require("God" in str(theos.get("gloss") or ""), "G2316 God gloss missing")

    shema_rows = (hebrew.get("strong_index") or {}).get("H8085G") or []
    require(bool(shema_rows), "H8085G Shema lexicon row missing")
    shema = hebrew["entries"][int(shema_rows[0])]
    require("hear" in str(shema.get("gloss") or "").lower(), "H8085G hear gloss missing")
    require("meaning" not in shema, "restricted Hebrew long Meaning field leaked into corpus")
    echad = lexicon_entry(hebrew, "H0259")
    require(str(echad.get("gloss") or "").lower() == "one", "H0259 echad gloss changed")

    require("V-IAI-3S" in (greek_morph.get("records") or {}), "Greek V-IAI-3S morphology expansion missing")
    require("HVqv2ms" in (hebrew_morph.get("records") or {}), "Hebrew HVqv2ms morphology expansion missing")

    jhn = load(root / "context" / "nt" / "JHN.json")
    j11 = (jhn.get("verses") or {}).get("1:1") or []
    require(len(j11) >= 17, "John 1:1 TAGNT context incomplete")
    require(j11[4].get("strong") == "G3056" and "Word" in str(j11[4].get("contextual_gloss") or ""), "John 1:1 Logos contextual gloss missing")
    j2119 = (jhn.get("verses") or {}).get("21:19") or []
    require(len(j2119) >= 16, "John 21:19 TAGNT context incomplete")
    require(j2119[3].get("strong") == "G4591" and "signif" in str(j2119[3].get("contextual_gloss") or "").lower(), "John 21:19 semaino contextual gloss missing")

    deu = load(root / "context" / "ot-semitic" / "DEU.json")
    d64 = (deu.get("verses") or {}).get("6:4") or []
    require(len(d64) >= 6, "Deuteronomy 6:4 TAHOT context incomplete")
    require(d64[0].get("root_strong") == "H8085G", "Deuteronomy 6:4 Shema strong tag missing")
    require("hear" in str(d64[0].get("contextual_gloss") or "").lower(), "Deuteronomy 6:4 Shema contextual gloss missing")
    require(d64[5].get("root_strong") == "H0259" and "one" in str(d64[5].get("contextual_gloss") or "").lower(), "Deuteronomy 6:4 echad contextual gloss missing")

    runtime = manifest.get("runtime_contract") or {}
    require(runtime.get("rahlfs_remains_separate_from_swete") is True, "Rahlfs/Swete semantic boundary changed")
    require(runtime.get("rahlfs_canonical_verse_identity_not_implied") is True, "Rahlfs canonical identity safety gate changed")
    require(runtime.get("hebrew_restricted_meaning_field_excluded") is True, "Hebrew rights safety gate changed")
    require(runtime.get("contextual_gloss_is_not_douay_token_alignment") is True, "DRA alignment disclaimer changed")

    print(
        "Logos semantic interlinear validation passed: "
        "73/73 books; NT context 27; Hebrew/Aramaic context 39; "
        "Greek OT Rahlfs lexical witness 46; John 1:1, John 21:19, Deut 6:4 acceptance tests passed"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
