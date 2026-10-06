#!/usr/bin/env python3
"""Validate Mercy ancient-text translation manifests and chapter files."""
from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
INDEX=ROOT/"data"/"ancient-text-translations"/"index.json"

def main()->int:
    data=json.loads(INDEX.read_text(encoding="utf-8"))
    failures=[]
    for work in data.get("works",[]):
        wid=work["id"]
        units=work.get("mercy_translation",{}).get("translated_units",[])
        seen=set()
        for unit in units:
            if unit in seen:
                failures.append(f"{wid}: duplicate translated unit {unit}")
                continue
            seen.add(unit)
            path=ROOT/"data"/"ancient-text-translations"/wid/f"{unit}.json"
            if not path.exists():
                failures.append(f"{wid}: missing {path.relative_to(ROOT)}")
                continue
            payload=json.loads(path.read_text(encoding="utf-8"))
            if payload.get("work_id")!=wid:
                failures.append(f"{wid}/{unit}: work_id mismatch")
            if not payload.get("mercy_translation",{}).get("text","").strip():
                failures.append(f"{wid}/{unit}: empty Mercy translation")
            if not payload.get("source_ref"):
                failures.append(f"{wid}/{unit}: missing source provenance")
        status=work.get("mercy_translation",{}).get("status","")
        if status.startswith("complete"):
            source_file=work.get("ancient_source",{}).get("source_file")
            if source_file:
                source=json.loads((ROOT/source_file).read_text(encoding="utf-8"))
                expected={f"chapter-{row['chapter']}" for row in source.get("chapters",[])}
                if set(units)!=expected:
                    failures.append(f"{wid}: complete status but translated units do not match full ancient source")
    if failures:
        print("Ancient-text translation validation FAILED")
        for f in failures: print(" -",f)
        return 1
    print("Ancient-text translation validation passed.")
    return 0

if __name__=="__main__":
    raise SystemExit(main())
