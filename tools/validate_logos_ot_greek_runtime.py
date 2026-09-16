#!/usr/bin/env python3
"""Validate the Catholic/Douay runtime mapping contract against a built OT Greek package."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "cloud-backend" / "app" / "logos_corpus" / "grc_ot_catholic_swete"
ISOLATED_ROOT = Path("sharealike/first1kgreek_swete_cc-by-sa-4.0")


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


def witness(root: Path, witness_id: str) -> dict:
    return load(root / ISOLATED_ROOT / "witnesses" / f"{witness_id}.json")


def refs(payload: dict) -> set[tuple[str | None, str]]:
    return {
        (row.get("source_chapter"), str(row.get("source_verse")))
        for row in (payload.get("verses") or [])
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    args = parser.parse_args()
    root = args.root.resolve()

    manifest = load(root / "manifest.json")
    mapping = load(root / "versification-map.json")
    need(manifest.get("production_enabled") is True, "runtime package is not production-enabled")
    need((manifest.get("mapping") or {}).get("fabricate_verse_boundaries") is False, "runtime package allows fabricated verse boundaries")

    identity = {row["canonical_book"]: row for row in mapping.get("identity_books") or []}
    expected_identity = {
        "TOB": "TOB-SWETE",
        "JDT": "JDT-SWETE",
        "1MA": "1MA-SWETE",
        "2MA": "2MA-SWETE",
        "WIS": "WIS-SWETE",
        "SIR": "SIR-SWETE",
    }
    need({book: row.get("witness_id") for book, row in identity.items()} == expected_identity, "identity-book runtime map changed")
    for book, witness_id in expected_identity.items():
        payload = witness(root, witness_id)
        need(("1", "1") in refs(payload), f"{book} runtime identity witness does not expose source 1:1")

    baruch = {row["witness_id"]: row for row in (mapping.get("baruch") or {}).get("segments") or []}
    need(baruch["BAR-SWETE"].get("canonical_locus") == "BAR 1-5", "Baruch 1-5 runtime map changed")
    need(baruch["EPJ-SWETE"].get("canonical_locus") == "BAR 6:1-n", "Baruch 6 runtime map changed")
    epj = witness(root, "EPJ-SWETE")
    need(len(epj.get("verses") or []) == 72, "Baruch 6 / Epistle of Jeremiah source count changed")

    esther = mapping.get("esther") or {}
    need(esther.get("mapping_granularity") == "component-range", "Esther runtime mapping must remain component-range")
    components = {row["component"]: row for row in esther.get("components") or []}
    need(components["B8-9"].get("canonical_locus") == "EST 15:1-3", "Esther B8-9 runtime Catholic range changed")
    need(components["B8-9"].get("mapping") == "component-range-no-forced-verse-split", "Esther B8-9 runtime safety rule changed")

    daniel = mapping.get("daniel") or {}
    need(daniel.get("primary_integration_witness") == "Theodotion", "Daniel runtime primary witness changed")
    need(daniel.get("parallel_witness") == "Old Greek", "Daniel runtime parallel witness changed")
    primary = {row["witness_id"]: row for row in daniel.get("primary_segments") or []}
    need(primary["DAN-TH-SWETE"].get("canonical_locus") == "DAN 3:24-90", "Daniel 3 runtime map changed")
    need(primary["SUS-TH-SWETE"].get("canonical_locus") == "DAN 13:1-64", "Daniel 13 runtime map changed")
    need(primary["BEL-TH-SWETE"].get("canonical_locus") == "DAN 14:1-42", "Daniel 14 runtime map changed")
    need(primary["BEL-TH-SWETE"].get("mapping") == "component-range-no-forced-verse-split", "Daniel 14 runtime mapping must remain component-range")

    dan = witness(root, "DAN-TH-SWETE")
    need(("3", "24") in refs(dan) and ("3", "90") in refs(dan), "Daniel 3:24-90 source evidence missing")
    sus = witness(root, "SUS-TH-SWETE")
    need(len(sus.get("verses") or []) == 64, "Daniel 13 / Susanna source count changed")
    bel = witness(root, "BEL-TH-SWETE")
    need(len(bel.get("verses") or []) == 36, "Daniel 14 / Bel source count changed")
    need(("1", "36") in refs(bel) and ("1", "42") not in refs(bel), "Daniel 14 must preserve 36-source-verse Bel boundary")

    parallel = {row["witness_id"]: row for row in daniel.get("parallel_segments") or []}
    need(set(parallel) == {"DAN-OG-SWETE", "SUS-OG-SWETE", "BEL-OG-SWETE"}, "Daniel Old Greek parallel runtime inventory changed")
    need(all(row.get("canonical_replacement") is False for row in parallel.values()), "Old Greek parallel witness cannot replace Theodotion")

    print(
        "Logos OT Greek runtime mapping contract passed: identity books, Baruch 6, Esther components, "
        "Daniel 3/13/14 and separate Old Greek/Theodotion witnesses preserved"
    )


if __name__ == "__main__":
    try:
        main()
    except ValidationError as exc:
        raise SystemExit(str(exc))
