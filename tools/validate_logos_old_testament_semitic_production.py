#!/usr/bin/env python3
"""Validate the production Hebrew/Aramaic OT package and DRA identity gate."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "heb_arc_oshb_wlc"
DRA_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "eng_douay_rheims_1899"
EXPECTED_ACCEPTANCE = "c93507c2f2d7e6cec6540ac9a6f155dd6eefecc9"
EXPECTED = {
    "masoretic_book_witness_count": 39,
    "chapter_count": 929,
    "verse_count": 23213,
    "token_count": 305507,
    "hebrew_token_count": 300679,
    "aramaic_token_count": 4828,
    "alignment_mismatch_count": 0,
}


class ValidationError(RuntimeError):
    pass


def load(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValidationError(f"cannot read {path}: {exc}") from exc


def need(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def token_rows(payload: dict):
    for chapter in (payload.get("chapters") or {}).values():
        for verse in chapter.values():
            yield from verse.get("tokens") or []


def dra_book_index() -> dict[str, dict]:
    manifest = load(DRA_ROOT / "manifest.json")
    return {str(row["id"]): row for row in manifest.get("books") or []}


def numeric_keys(chapter: dict) -> set[int] | None:
    keys: set[int] = set()
    for key in chapter:
        text = str(key)
        if not text.isdigit():
            return None
        keys.add(int(text))
    return keys


def validate(root: Path) -> None:
    manifest = load(root / "manifest.json")
    need(manifest.get("corpus_id") == "heb_arc_oshb_wlc", "unexpected OT Semitic corpus id")
    need(manifest.get("corpus_version") == "2026.09.16-oshb-wlc-39", "unexpected OT Semitic corpus version")
    need(manifest.get("production_enabled") is True, "OT Semitic production package is disabled")
    need(manifest.get("languages") == ["he", "arc"], "OT Semitic language contract changed")

    accepted = manifest.get("phase1a_acceptance") or {}
    need(accepted.get("merge_commit") == EXPECTED_ACCEPTANCE, "Phase 1A owner-acceptance merge changed")
    for key, expected in EXPECTED.items():
        need(int(accepted.get(key) or 0) == expected, f"production acceptance {key} changed")

    source = manifest.get("source") or {}
    need(source.get("repository") == "openscriptures/morphhb", "unexpected OSHB source repository")
    need(source.get("commit") == "3d15126fb1ef74867fc1434be1942e837932691f", "OSHB commit changed")
    need(source.get("tree_sha") == "dd2fe9d2168f3fc0963bcdbdac8fa1d487c06e45", "WLC tree pin changed")
    need(source.get("surface_rights") == "Public Domain", "WLC surface rights changed")
    need(source.get("linguistic_annotation_license") == "CC BY 4.0", "OSHB linguistic license changed")

    parts = manifest.get("partitions") or {}
    need((parts.get("surface") or {}).get("rights") == "Public Domain", "surface partition rights changed")
    need((parts.get("linguistics") or {}).get("license") == "CC BY 4.0", "linguistics partition license changed")
    need((parts.get("alignment") or {}).get("mismatch_count") == 0, "alignment partition mismatch")

    vers = manifest.get("versification") or {}
    need(vers.get("runtime_exact_identity_required") is True, "runtime identity gate missing")
    need(vers.get("automatic_remapping") is False, "silent MT-to-DRA remapping enabled")
    need(vers.get("fabricate_verse_boundaries") is False, "verse-boundary fabrication enabled")
    need(vers.get("mismatched_chapters_blocked_until_explicit_mapping") is True, "mismatched chapter block missing")

    layers = manifest.get("derived_layers") or {}
    need(layers.get("glosses") is False and layers.get("transliteration") is False, "unapproved gloss/transliteration enabled")
    need(layers.get("lemmata") is True and layers.get("morphology") is True, "source linguistic annotations missing")
    need(layers.get("lemma_morphology_are_source_annotations") is True, "source annotation provenance marker missing")

    phase = root / "phase1a"
    phase_manifest = load(phase / "manifest.json")
    need(phase_manifest.get("production_enabled") is False, "embedded Phase 1A evidence must remain validation-only")
    for key, expected in EXPECTED.items():
        need(int(phase_manifest.get(key) or 0) == expected, f"embedded Phase 1A {key} changed")
    need(phase_manifest.get("surface_normalization_applied") is False, "source normalization changed")

    book_ids = [str(row.get("book_id")) for row in phase_manifest.get("books") or []]
    need(len(book_ids) == 39 and len(set(book_ids)) == 39, "expected 39 unique Semitic book ids")
    for partition in ("surface", "linguistics", "alignment"):
        files = {p.stem for p in (phase / partition).glob("*.json")}
        need(files == set(book_ids), f"{partition} package inventory mismatch")

    # Strong source/token spot checks retained from accepted Phase 1A.
    gen_surface = load(phase / "surface" / "GEN.json")
    gen_ling = load(phase / "linguistics" / "GEN.json")
    first_surface = gen_surface["chapters"]["1"]["1"]["tokens"][0]
    first_ling = gen_ling["chapters"]["1"]["1"]["tokens"][0]
    need(first_surface["surface"] == "בְּ/רֵאשִׁ֖ית", "Genesis 1:1 source surface changed")
    need(first_ling["lemma"] == "b/7225", "Genesis 1:1 lemma changed")
    need(first_ling["morphology"] == "HR/Ncfsa", "Genesis 1:1 morphology changed")
    need(first_ling["source_word_id"] == "01xeN", "Genesis 1:1 source word id changed")

    dan = load(phase / "linguistics" / "DAN.json")
    dan24 = dan["chapters"]["2"]["4"]["tokens"]
    need({str(row["language"]) for row in dan24} == {"he", "arc"}, "Daniel 2:4 Hebrew/Aramaic transition lost")

    # Runtime DRA identity authorization is chapter-scoped. Genesis 1 is the
    # first public acceptance case and must match exactly before it can serve.
    dra_index = dra_book_index()
    dra_gen = load(DRA_ROOT / str(dra_index["GEN"]["filename"]))
    source_gen1 = gen_surface["chapters"]["1"]
    dra_gen1 = (dra_gen.get("chapters") or {}).get("1") or {}
    source_keys = numeric_keys(source_gen1)
    dra_keys = numeric_keys(dra_gen1)
    need(source_keys is not None and dra_keys is not None, "Genesis 1 contains nonnumeric verse ids")
    need(source_keys == dra_keys, "Genesis 1 OSHB/DRA verse identities do not match exactly")

    # Every packaged token must stay free of fabricated gloss/transliteration.
    for bid in book_ids:
        surface = load(phase / "surface" / f"{bid}.json")
        ling = load(phase / "linguistics" / f"{bid}.json")
        st = list(token_rows(surface))
        lt = list(token_rows(ling))
        need(len(st) == len(lt), f"token partition length mismatch: {bid}")
        for left, right in zip(st, lt):
            need(left.get("id") == right.get("id"), f"token id partition mismatch: {bid}")
            need("gloss" not in left and "transliteration" not in left, f"fabricated surface derived field: {bid}")
            need("gloss" not in right and "transliteration" not in right, f"fabricated linguistic derived field: {bid}")

    print("Logos OT Hebrew/Aramaic production package + Genesis 1 DRA identity gate: OK")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    validate(args.root)


if __name__ == "__main__":
    try:
        main()
    except ValidationError as exc:
        raise SystemExit(f"OT Semitic production validation failed: {exc}") from exc
