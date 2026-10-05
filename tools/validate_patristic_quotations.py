#!/usr/bin/env python3
"""Validate the curated patristic quotation index against the vendored corpus."""
from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
QUOTES = ROOT / "data" / "patristic-quotations.json"
CORPUS = ROOT / "data" / "patristic-corpus"

def norm(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()

def main() -> int:
    data = json.loads(QUOTES.read_text(encoding="utf-8"))
    corpus_index = json.loads((CORPUS / "index.json").read_text(encoding="utf-8"))
    sources = {row["id"]: row for row in corpus_index["sources"]}
    failures: list[str] = []

    for row in data["quotations"]:
        sid = row["source_id"]
        if sid not in sources:
            failures.append(f"{row['id']}: unknown source_id {sid}")
            continue
        source = sources[sid]
        source_index = json.loads((CORPUS / source["index"]).read_text(encoding="utf-8"))
        toc = next((x for x in source_index["toc"] if x["index"] == row["section_index"]), None)
        if not toc:
            failures.append(f"{row['id']}: missing section {row['section_index']}")
            continue
        section_path = CORPUS / source["corpus"] / sid / toc["file"]
        section = json.loads(section_path.read_text(encoding="utf-8"))
        pi = row["paragraph_index"]
        paragraphs = section.get("paragraphs", [])
        if pi < 0 or pi >= len(paragraphs):
            failures.append(f"{row['id']}: invalid paragraph_index {pi}")
            continue
        if norm(row["quote"]) not in norm(paragraphs[pi]):
            failures.append(f"{row['id']}: quote is not an exact normalized substring of source paragraph")
        for key in ("work","locator","edition","publication_year","rights","context","reader_url"):
            if not row.get(key):
                failures.append(f"{row['id']}: missing {key}")

    if failures:
        print("Patristic quotation validation FAILED")
        for failure in failures:
            print(" -", failure)
        return 1
    print(f"Patristic quotation validation passed: {len(data['quotations'])} verified quotations.")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
