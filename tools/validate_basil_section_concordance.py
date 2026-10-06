#!/usr/bin/env python3
"""Check Basil's editorial section concordance without mistaking OCR for verified Greek."""
from __future__ import annotations
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data/ancient-text-sources/basil-de-spiritu-sancto-ocr.json"
MAP = ROOT / "data/ancient-text-sources/basil-section-concordance.json"
TRANSLATIONS = ROOT / "data/ancient-text-translations/index.json"

def main() -> int:
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    audit = json.loads(MAP.read_text(encoding="utf-8"))
    index = json.loads(TRANSLATIONS.read_text(encoding="utf-8"))
    chapters = audit["chapters"]
    sections = audit["sections"]
    assert len(chapters) == audit["expected_chapters"] == 30
    assert len(sections) == audit["expected_sections"] == 79
    assert [c["chapter"] for c in chapters] == list(range(1, 31))
    assert [s["section"] for s in sections] == list(range(1, 80))
    assert [s["chapter"] for s in sections] == [
        c["chapter"] for c in chapters
        for _ in range(c["start_section"], c["end_section"] + 1)
    ]
    rows = source["rows"]
    located = 0
    for record in sections:
        anchor = record["source_anchor"]
        if anchor is None:
            continue
        located += 1
        row = rows[anchor["row_index"]]
        assert row["locus"] == anchor["locus"], record
        assert row["text"].lstrip().startswith(str(record["section"]) + "."), record
    assert located == audit["summary"]["located_ocr_anchors"]
    work = next(w for w in index["works"] if w["id"] == audit["work_id"])
    for unit in work["mercy_translation"]["translated_units"]:
        p = ROOT / "data/ancient-text-translations" / audit["work_id"] / (unit + ".json")
        assert p.is_file(), p
        item = json.loads(p.read_text(encoding="utf-8"))
        assert item["work_id"] == audit["work_id"]
        assert item["mercy_translation"]["text"].strip()
    print(f"Basil section concordance: PASS — 30 chapters, 79 sections, {located} OCR anchor(s), {79-located} missing.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
