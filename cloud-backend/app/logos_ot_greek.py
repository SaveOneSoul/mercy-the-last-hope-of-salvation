import json
from functools import lru_cache
from pathlib import Path

from fastapi import APIRouter, HTTPException, Query, Response

from .logos import _parse_corpus_reference


router = APIRouter(prefix="/ot-greek", tags=["Logos Greek Old Testament"])
CORPUS_DIR = Path(__file__).with_name("logos_corpus") / "grc_ot_catholic_swete"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"
MAPPING_PATH = CORPUS_DIR / "versification-map.json"
ISOLATED_ROOT = CORPUS_DIR / "sharealike" / "first1kgreek_swete_cc-by-sa-4.0"
WITNESS_DIR = ISOLATED_ROOT / "witnesses"
EXPECTED_ACCEPTANCE_MERGE = "22ad0019355d6924592d3c6b5176624e6fd4c866"


@lru_cache(maxsize=1)
def _ot_greek_manifest() -> dict:
    if not MANIFEST_PATH.exists():
        return {}
    with MANIFEST_PATH.open("r", encoding="utf-8") as handle:
        manifest = json.load(handle)
    if manifest.get("corpus_id") != "grc_ot_catholic_swete":
        raise RuntimeError("Unexpected Logos OT Greek corpus id")
    if manifest.get("production_enabled") is not True:
        raise RuntimeError("Logos OT Greek corpus is not production-enabled")
    accepted = manifest.get("phase1b_acceptance") or {}
    if accepted.get("merge_commit") != EXPECTED_ACCEPTANCE_MERGE:
        raise RuntimeError("Unexpected Logos OT Greek Phase 1B acceptance merge")
    if int(accepted.get("witness_count") or 0) != 15:
        raise RuntimeError("Logos OT Greek corpus does not contain 15 accepted witnesses")
    if int(accepted.get("source_verse_record_count") or 0) != 5337:
        raise RuntimeError("Logos OT Greek source verse total changed")
    return manifest


@lru_cache(maxsize=1)
def _ot_greek_mapping() -> dict:
    if not MAPPING_PATH.exists():
        return {}
    with MAPPING_PATH.open("r", encoding="utf-8") as handle:
        mapping = json.load(handle)
    if mapping.get("production_enabled") is not False:
        raise RuntimeError("Accepted OT Greek mapping evidence must remain validation-only metadata")
    return mapping


@lru_cache(maxsize=32)
def _witness(witness_id: str) -> dict:
    safe = "".join(ch for ch in str(witness_id).upper() if ch.isalnum() or ch == "-")
    if safe != str(witness_id).upper():
        raise RuntimeError("Invalid OT Greek witness id")
    path = WITNESS_DIR / f"{safe}.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="logos_ot_greek_witness_not_installed")
    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if payload.get("license") != "CC BY-SA 4.0":
        raise RuntimeError("Unexpected OT Greek witness licence")
    if payload.get("share_alike") is not True or payload.get("isolation_required") is not True:
        raise RuntimeError("OT Greek witness isolation metadata missing")
    return payload


def _require_installed() -> tuple[dict, dict]:
    manifest = _ot_greek_manifest()
    mapping = _ot_greek_mapping()
    if not manifest or not mapping:
        raise HTTPException(status_code=404, detail="logos_ot_greek_corpus_not_installed")
    return manifest, mapping


def _canonical_reference(book: str, chapter: int, verse_start: int | None, verse_end: int | None) -> str:
    if verse_start is None:
        return f"{book} {chapter}"
    if verse_end is not None and verse_end != verse_start:
        return f"{book} {chapter}:{verse_start}-{verse_end}"
    return f"{book} {chapter}:{verse_start}"


def _public_verse(row: dict) -> dict:
    return {
        "source_chapter": row.get("source_chapter"),
        "source_verse": row.get("source_verse"),
        "source_reference": row.get("source_reference"),
        "surface": row.get("surface"),
    }


def _rows_for_exact_reference(
    witness: dict,
    source_chapter: str | None,
    verse_start: int | None,
    verse_end: int | None,
    *,
    allowed_start: int | None = None,
    allowed_end: int | None = None,
) -> list[dict]:
    rows = [
        row
        for row in (witness.get("verses") or [])
        if row.get("source_chapter") == source_chapter
    ]
    numeric = {
        int(str(row.get("source_verse"))): row
        for row in rows
        if str(row.get("source_verse")).isdigit()
    }
    if allowed_start is not None:
        numeric = {number: row for number, row in numeric.items() if number >= allowed_start}
    if allowed_end is not None:
        numeric = {number: row for number, row in numeric.items() if number <= allowed_end}
    if verse_start is None:
        selected = [numeric[number] for number in sorted(numeric)]
        if not selected:
            raise HTTPException(status_code=404, detail="logos_ot_greek_source_segment_not_found")
        return selected
    end = verse_end or verse_start
    selected = []
    for number in range(verse_start, end + 1):
        if allowed_start is not None and number < allowed_start:
            raise HTTPException(status_code=404, detail="logos_ot_greek_reference_not_in_accepted_scope")
        if allowed_end is not None and number > allowed_end:
            raise HTTPException(status_code=404, detail="logos_ot_greek_reference_not_in_accepted_scope")
        row = numeric.get(number)
        if row is None:
            raise HTTPException(status_code=404, detail="logos_ot_greek_source_verse_not_found")
        selected.append(row)
    return selected


def _rows_by_verse_number(witness: dict, verse_start: int | None, verse_end: int | None) -> list[dict]:
    rows = witness.get("verses") or []
    numeric: dict[int, list[dict]] = {}
    for row in rows:
        verse = str(row.get("source_verse"))
        if verse.isdigit():
            numeric.setdefault(int(verse), []).append(row)
    if verse_start is None:
        return rows
    end = verse_end or verse_start
    selected = []
    for number in range(verse_start, end + 1):
        matches = numeric.get(number) or []
        if len(matches) != 1:
            raise HTTPException(status_code=404, detail="logos_ot_greek_source_verse_not_unique")
        selected.append(matches[0])
    return selected


def _witness_public(witness: dict, rows: list[dict], mapping: dict) -> dict:
    source = witness.get("source") or {}
    return {
        "witness_id": witness.get("witness_id"),
        "name": witness.get("name"),
        "canonical_scope": witness.get("canonical_scope"),
        "witness_role": witness.get("witness_role"),
        "license": witness.get("license"),
        "share_alike": witness.get("share_alike"),
        "isolation_required": witness.get("isolation_required"),
        "source": {
            "repository": source.get("repository"),
            "commit": source.get("commit"),
            "edition_urn": source.get("edition_urn"),
            "text_git_blob_sha1": source.get("text_git_blob_sha1"),
            "text_sha256": source.get("text_sha256"),
            "per_file_license_verified": source.get("per_file_license_verified"),
        },
        "mapping": mapping,
        "verses": [_public_verse(row) for row in rows],
    }


def _identity_map(mapping: dict) -> dict[str, dict]:
    return {
        str(row.get("canonical_book")): row
        for row in (mapping.get("identity_books") or [])
    }


def _esther_components(chapter: int, verse_start: int | None, verse_end: int | None, mapping: dict) -> list[dict]:
    components = {str(row.get("component")): row for row in ((mapping.get("esther") or {}).get("components") or [])}

    def component_for(ch: int, verse: int) -> str | None:
        if ch == 10 and 4 <= verse <= 13:
            return "F1-10"
        if ch == 11 and verse == 1:
            return "F11-postscript"
        if ch == 11 and verse >= 2:
            return "A"
        if ch == 12 and 1 <= verse <= 6:
            return "A"
        if ch == 13 and 1 <= verse <= 7:
            return "B1-7"
        if ch == 13 and verse >= 8:
            return "C"
        if ch == 14 and 1 <= verse <= 19:
            return "C"
        if ch == 15 and 1 <= verse <= 3:
            return "B8-9"
        if ch == 15 and 4 <= verse <= 19:
            return "D"
        if ch == 16 and 1 <= verse <= 24:
            return "E"
        return None

    if verse_start is None:
        chapter_components = {
            10: ["F1-10"],
            11: ["F11-postscript", "A"],
            12: ["A"],
            13: ["B1-7", "C"],
            14: ["C"],
            15: ["B8-9", "D"],
            16: ["E"],
        }.get(chapter, [])
        return [components[key] for key in chapter_components if key in components]

    selected_names: list[str] = []
    for verse in range(verse_start, (verse_end or verse_start) + 1):
        component = component_for(chapter, verse)
        if component is None:
            raise HTTPException(status_code=404, detail="logos_ot_greek_reference_not_in_accepted_scope")
        if component not in selected_names:
            selected_names.append(component)
    return [components[name] for name in selected_names]


def _parallel_daniel(chapter: int, manifest: dict) -> list[dict]:
    if chapter == 3:
        witness = _witness("DAN-OG-SWETE")
        rows = _rows_for_exact_reference(witness, "3", None, None, allowed_start=24, allowed_end=90)
        mapping = {
            "mode": "preserved-parallel-witness",
            "canonical_replacement": False,
            "canonical_locus": "DAN 3:24-90",
        }
        return [_witness_public(witness, rows, mapping)]
    if chapter == 13:
        witness = _witness("SUS-OG-SWETE")
        return [
            _witness_public(
                witness,
                witness.get("verses") or [],
                {"mode": "preserved-parallel-witness", "canonical_replacement": False, "canonical_locus": "DAN 13"},
            )
        ]
    if chapter == 14:
        witness = _witness("BEL-OG-SWETE")
        return [
            _witness_public(
                witness,
                witness.get("verses") or [],
                {"mode": "preserved-parallel-witness", "canonical_replacement": False, "canonical_locus": "DAN 14"},
            )
        ]
    return []


def _study_payload(reference: str) -> dict:
    manifest, mapping = _require_installed()
    book_meta, chapter, verse_start, verse_end = _parse_corpus_reference(reference)
    if str(book_meta.get("testament")) != "OT":
        raise HTTPException(status_code=404, detail="logos_ot_greek_ot_reference_required")

    book_id = str(book_meta.get("id"))
    book_name = str(book_meta.get("name"))
    supported = set(((manifest.get("witnesses") or {}).get("supported_canonical_books") or []))
    if book_id not in supported:
        raise HTTPException(status_code=404, detail="logos_ot_greek_reference_not_in_accepted_scope")

    identity = _identity_map(mapping)
    primary: dict
    parallel: list[dict] = []

    identity_row = identity.get(book_id)
    if identity_row:
        witness = _witness(str(identity_row["witness_id"]))
        rows = _rows_for_exact_reference(witness, str(chapter), verse_start, verse_end)
        primary = _witness_public(
            witness,
            rows,
            {
                **identity_row,
                "mode": "identity-chapter-verse",
                "exact_verse_alignment": True,
            },
        )
    elif book_id == "BAR":
        segments = {str(row.get("witness_id")): row for row in ((mapping.get("baruch") or {}).get("segments") or [])}
        if 1 <= chapter <= 5:
            row = segments["BAR-SWETE"]
            witness = _witness("BAR-SWETE")
            rows = _rows_for_exact_reference(witness, str(chapter), verse_start, verse_end)
            primary = _witness_public(witness, rows, {**row, "mode": "identity-chapter-verse", "exact_verse_alignment": True})
        elif chapter == 6:
            row = segments["EPJ-SWETE"]
            witness = _witness("EPJ-SWETE")
            rows = _rows_by_verse_number(witness, verse_start, verse_end)
            primary = _witness_public(witness, rows, {**row, "mode": "source-verse-to-canonical-chapter-6", "exact_verse_alignment": True})
        else:
            raise HTTPException(status_code=404, detail="logos_ot_greek_reference_not_in_accepted_scope")
    elif book_id == "EST":
        components = _esther_components(chapter, verse_start, verse_end, mapping)
        if not components:
            raise HTTPException(status_code=404, detail="logos_ot_greek_reference_not_in_accepted_scope")
        witness = _witness("EST-SWETE")
        primary = _witness_public(
            witness,
            witness.get("verses") or [],
            {
                "mode": "component-range",
                "exact_verse_alignment": False,
                "requested_components": components,
                "source_selection": "full-integrated-esther-witness",
                "note": "The accepted mapping is component-level. The API does not manufacture a one-to-one Greek/Douay verse split.",
            },
        )
    elif book_id == "DAN":
        primary_segments = {str(row.get("witness_id")): row for row in ((mapping.get("daniel") or {}).get("primary_segments") or [])}
        if chapter == 3:
            if verse_start is not None and (verse_start < 24 or (verse_end or verse_start) > 90):
                raise HTTPException(status_code=404, detail="logos_ot_greek_reference_not_in_accepted_scope")
            row = primary_segments["DAN-TH-SWETE"]
            witness = _witness("DAN-TH-SWETE")
            rows = _rows_for_exact_reference(witness, "3", verse_start, verse_end, allowed_start=24, allowed_end=90)
            primary = _witness_public(witness, rows, {**row, "mode": "identity-chapter-verse-range", "exact_verse_alignment": True})
            parallel = _parallel_daniel(chapter, manifest)
        elif chapter == 13:
            if verse_start is not None and (verse_start < 1 or (verse_end or verse_start) > 64):
                raise HTTPException(status_code=404, detail="logos_ot_greek_reference_not_in_accepted_scope")
            row = primary_segments["SUS-TH-SWETE"]
            witness = _witness("SUS-TH-SWETE")
            rows = _rows_for_exact_reference(witness, "1", verse_start, verse_end, allowed_start=1, allowed_end=64)
            primary = _witness_public(witness, rows, {**row, "mode": "source-verse-to-canonical-chapter-13", "exact_verse_alignment": True})
            parallel = _parallel_daniel(chapter, manifest)
        elif chapter == 14:
            if verse_start is not None and (verse_start < 1 or (verse_end or verse_start) > 42):
                raise HTTPException(status_code=404, detail="logos_ot_greek_reference_not_in_accepted_scope")
            row = primary_segments["BEL-TH-SWETE"]
            witness = _witness("BEL-TH-SWETE")
            primary = _witness_public(
                witness,
                witness.get("verses") or [],
                {
                    **row,
                    "mode": "component-range-no-forced-verse-split",
                    "exact_verse_alignment": False,
                    "requested_canonical_reference": _canonical_reference(book_name, chapter, verse_start, verse_end),
                    "note": "The pinned Theodotion witness has 36 source verse divisions while Douay-Rheims Daniel 14 has 42. All 36 source rows are returned without inventing six Greek boundaries.",
                },
            )
            parallel = _parallel_daniel(chapter, manifest)
        else:
            raise HTTPException(status_code=404, detail="logos_ot_greek_reference_not_in_accepted_scope")
    else:
        raise HTTPException(status_code=404, detail="logos_ot_greek_reference_not_in_accepted_scope")

    return {
        "reference": _canonical_reference(book_name, chapter, verse_start, verse_end),
        "book": book_name,
        "book_id": book_id,
        "chapter": chapter,
        "verse_start": verse_start,
        "verse_end": verse_end,
        "language": "grc",
        "label": "Catholic Old Testament Greek — accepted Swete witnesses",
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "primary_witness": primary,
        "parallel_witnesses": parallel,
        "derived_layers": manifest.get("derived_layers") or {},
        "mapping_contract": manifest.get("mapping") or {},
        "note": (
            "Greek source verse boundaries are preserved. Exact verse alignment is exposed only where the accepted mapping verifies it; "
            "Esther and Daniel 14 remain component-range mappings where source and Douay-Rheims boundaries differ."
        ),
    }


@router.get("/catalog")
def logos_ot_greek_catalog(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest = _ot_greek_manifest()
    accepted = manifest.get("phase1b_acceptance") or {}
    witnesses = manifest.get("witnesses") or {}
    return {
        "installed": bool(manifest),
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "language": manifest.get("language"),
        "scope": manifest.get("scope"),
        "witness_count": accepted.get("witness_count", 0),
        "source_verse_record_count": accepted.get("source_verse_record_count", 0),
        "primary_integration_witness_count": accepted.get("primary_integration_witness_count", 0),
        "parallel_witness_count": accepted.get("parallel_witness_count", 0),
        "supported_canonical_books": witnesses.get("supported_canonical_books") or [],
        "production_enabled": manifest.get("production_enabled", False),
    }


@router.get("/source-rights")
def logos_ot_greek_source_rights(response: Response):
    response.headers["Cache-Control"] = "public, max-age=300"
    manifest, mapping = _require_installed()
    return {
        "corpus_id": manifest.get("corpus_id"),
        "corpus_version": manifest.get("corpus_version"),
        "source": manifest.get("source") or {},
        "partition": manifest.get("partition") or {},
        "derived_layers": manifest.get("derived_layers") or {},
        "mapping_contract": manifest.get("mapping") or {},
        "runtime_contract": manifest.get("runtime_contract") or {},
        "serving_contract": manifest.get("serving_contract") or {},
        "accepted_versification_policy": mapping.get("mapping_policy") or {},
    }


@router.get("/interlinear")
def logos_ot_greek_interlinear(
    reference: str = Query(min_length=2, max_length=120),
    response: Response = None,
):
    if response is not None:
        response.headers["Cache-Control"] = "no-store, max-age=0"
    return _study_payload(reference)
