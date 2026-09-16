#!/usr/bin/env python3
"""Generate the deterministic Logos versification-resolution burn-down report."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INTERLINEAR = ROOT / "cloud-backend" / "app" / "logos_interlinear"
VERS = INTERLINEAR / "versification"
DEFAULT_COVERAGE = INTERLINEAR / "coverage-audit.json"
DEFAULT_JSON = VERS / "resolution-audit.json"
DEFAULT_MARKDOWN = ROOT / "LOGOS_VERSIFICATION_RESOLUTION.md"
RESOLVED_NATIVE_STATUSES = {
    "exact-all-chapters",
    "verified-explicit-map",
    "component-range-mapping",
    "mixed-exact-and-component-range",
}
LANES = ("semitic", "greek", "latin")


class AuditError(RuntimeError):
    pass


def load(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"cannot read {path}: {exc}") from exc


def require(condition: bool, message: str) -> None:
    if not condition:
        raise AuditError(message)


def registry_documents(registry: dict[str, Any]) -> dict[tuple[str, str], dict[str, Any]]:
    out: dict[tuple[str, str], dict[str, Any]] = {}
    for entry in registry.get("mappings") or []:
        book_id = str(entry.get("book_id") or "").upper()
        lane = str(entry.get("lane") or "").lower()
        filename = str(entry.get("file") or "")
        path = (VERS / filename).resolve()
        require(VERS.resolve() in path.parents, f"mapping escapes registry root: {filename}")
        require(path.exists(), f"registered mapping missing: {filename}")
        document = load(path)
        out[(book_id, lane)] = {"entry": entry, "document": document}
    return out


def registry_resolution(
    docs: dict[tuple[str, str], dict[str, Any]],
    book_id: str,
    lane: str,
    mismatches: list[dict[str, Any]],
) -> dict[str, Any] | None:
    bundle = docs.get((book_id, lane))
    if not bundle:
        return None
    entry = bundle["entry"]
    document = bundle["document"]
    coverage = document.get("coverage") or {}
    audited = {str(row.get("chapter")) for row in mismatches}
    covered = {str(value) for value in coverage.get("audited_mismatch_chapters") or []}
    verified = (
        entry.get("status") == "verified"
        and document.get("status") == "verified"
        and coverage.get("complete_for_audited_mismatches") is True
        and audited == covered
        and bool(audited)
    )
    return {
        "status": "verified-registry-map" if verified else "registered-unresolved",
        "verified": verified,
        "mapping_version": document.get("mapping_version"),
        "file": entry.get("file"),
        "covered_chapters": sorted(covered, key=lambda value: int(value) if value.isdigit() else value),
    }


def build(coverage: dict[str, Any], registry: dict[str, Any]) -> dict[str, Any]:
    books = coverage.get("books") or []
    require(len(books) == 73, f"coverage audit must contain 73 books, found {len(books)}")
    docs = registry_documents(registry)
    rows: list[dict[str, Any]] = []
    unresolved_books = 0
    unresolved_lane_count = 0
    verified_registry_lane_count = 0
    native_resolved_lane_count = 0
    exact_lane_count = 0

    for book in books:
        book_id = str(book.get("id"))
        lane_rows: dict[str, Any] = {}
        book_unresolved = False
        for lane in LANES:
            lane_payload = book.get(lane) or {}
            if lane_payload.get("status") == "not-applicable":
                lane_rows[lane] = {"status": "not-applicable"}
                continue
            vers = lane_payload.get("versification") or {}
            status = str(vers.get("status") or "")
            mismatches = list(vers.get("mismatches") or [])
            mismatch_chapters = [str(row.get("chapter")) for row in mismatches]
            if status == "exact-all-chapters":
                lane_rows[lane] = {"status": "exact", "mismatch_chapters": []}
                exact_lane_count += 1
                continue
            if status in RESOLVED_NATIVE_STATUSES - {"exact-all-chapters"}:
                lane_rows[lane] = {
                    "status": "resolved-existing-map",
                    "mapping_mode": status,
                    "mismatch_chapters": mismatch_chapters,
                }
                native_resolved_lane_count += 1
                continue
            registered = registry_resolution(docs, book_id, lane, mismatches)
            if registered and registered.get("verified"):
                lane_rows[lane] = {
                    **registered,
                    "mismatch_chapters": mismatch_chapters,
                }
                verified_registry_lane_count += 1
                continue
            lane_rows[lane] = {
                "status": "unresolved",
                "source_status": status or "unknown",
                "mismatch_chapters": mismatch_chapters,
                "registry": registered,
            }
            book_unresolved = True
            unresolved_lane_count += 1

        if book_unresolved:
            unresolved_books += 1
        rows.append(
            {
                "order": book.get("order"),
                "id": book_id,
                "book": book.get("book"),
                "testament": book.get("testament"),
                "unresolved": book_unresolved,
                "lanes": lane_rows,
            }
        )

    return {
        "schema_version": 1,
        "audit_version": "2026.09.17-v1",
        "canonical_reference_system": "douay-rheims-1899",
        "policy": {
            "source_text_immutable": True,
            "automatic_remapping_forbidden": True,
            "verified_mapping_required_for_resolution": True,
        },
        "summary": {
            "book_count": 73,
            "books_unresolved": unresolved_books,
            "books_resolved": 73 - unresolved_books,
            "unresolved_lane_count": unresolved_lane_count,
            "verified_registry_lane_count": verified_registry_lane_count,
            "native_resolved_lane_count": native_resolved_lane_count,
            "exact_lane_count": exact_lane_count,
        },
        "books": rows,
    }


def render(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = [
        "# Logos Versification Resolution Audit",
        "",
        "Generated deterministically from `coverage-audit.json` plus the verified versification registry. Source Scripture corpora are never rewritten by this report.",
        "",
        "## Burn-down",
        "",
        f"- Catholic books: **{summary['book_count']}**",
        f"- Books with at least one unresolved lane: **{summary['books_unresolved']}**",
        f"- Books with all applicable lanes resolved/exact: **{summary['books_resolved']}**",
        f"- Unresolved source lanes: **{summary['unresolved_lane_count']}**",
        f"- Lanes resolved by new verified registry maps: **{summary['verified_registry_lane_count']}**",
        f"- Lanes already resolved by accepted component/explicit maps: **{summary['native_resolved_lane_count']}**",
        "",
        "A book leaves the unresolved count only when every applicable Hebrew/Aramaic, Greek, and Latin lane is exact or backed by a verified explicit/component mapping.",
        "",
        "## Per-book status",
        "",
        "| # | Book | T | Semitic | Greek | Latin | Overall |",
        "|---:|---|:--:|---|---|---|---|",
    ]
    for row in report["books"]:
        cells = []
        for lane in LANES:
            lane_row = row["lanes"][lane]
            status = lane_row.get("status")
            if status == "not-applicable":
                text = "—"
            elif status == "exact":
                text = "Exact"
            elif status == "verified-registry-map":
                text = "Verified map"
            elif status == "resolved-existing-map":
                text = "Existing verified/component map"
            else:
                chapters = lane_row.get("mismatch_chapters") or []
                text = f"Unresolved ({len(chapters)} ch)" if chapters else "Unresolved"
            cells.append(text)
        lines.append(
            "| "
            + " | ".join(
                [
                    str(row.get("order")),
                    str(row.get("book")),
                    str(row.get("testament")),
                    *cells,
                    "Unresolved" if row.get("unresolved") else "Resolved",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Acceptance rule",
            "",
            "The target is **0 unresolved books**. A mapping may reduce the burn-down only after the mapping file is `verified`, its audited mismatch chapters exactly match current corpus evidence, all enumerated references exist, and the mapping validator passes bidirectionally.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--coverage", type=Path, default=DEFAULT_COVERAGE)
    parser.add_argument("--json-output", type=Path, default=DEFAULT_JSON)
    parser.add_argument("--markdown-output", type=Path, default=DEFAULT_MARKDOWN)
    args = parser.parse_args()
    coverage = load(args.coverage)
    registry = load(VERS / "index.json")
    report = build(coverage, registry)
    args.json_output.parent.mkdir(parents=True, exist_ok=True)
    args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
    args.json_output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    args.markdown_output.write_text(render(report), encoding="utf-8")
    summary = report["summary"]
    print(
        "Logos versification resolution audit passed: "
        f"{summary['books_unresolved']} unresolved book(s), "
        f"{summary['unresolved_lane_count']} unresolved lane(s), "
        f"{summary['verified_registry_lane_count']} lane(s) resolved by registry"
    )
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except AuditError as exc:
        raise SystemExit(f"Logos versification resolution audit failed: {exc}") from exc
