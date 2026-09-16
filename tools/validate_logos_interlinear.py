#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INTERLINEAR_DIR = ROOT / "cloud-backend" / "app" / "logos_interlinear"
SOURCES_PATH = INTERLINEAR_DIR / "sources-manifest.json"
BOOKS_PATH = INTERLINEAR_DIR / "books.json"
TOKEN_SCHEMA_PATH = INTERLINEAR_DIR / "token.schema.json"
PHASE1B_ACCEPTANCE_MERGE = "22ad0019355d6924592d3c6b5176624e6fd4c866"
VULGATE_COMMIT = "f257a3559025c3f873b48a75019f53a9354ed7de"
VULGATE_BLOB = "c0e65106383658fd914e90da4c82f2be48a0a762"
VULGATE_RIGHTS_BLOB = "50caf5d5b86fb69471c1b849584cc476a7944df5"

DEUTEROCANON = {
    "Tobit", "Judith", "Wisdom", "Sirach", "Baruch", "1 Maccabees", "2 Maccabees",
}
REQUIRED_DANIEL_ADDITIONS = {
    "Prayer of Azariah and Song of the Three Young Men", "Susanna", "Bel and the Dragon",
}


def fail(message: str) -> None:
    raise SystemExit(f"Logos interlinear validation failed: {message}")


def load_json(path: Path) -> dict:
    if not path.exists():
        fail(f"missing {path.relative_to(ROOT)}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        fail(f"cannot parse {path.relative_to(ROOT)}: {exc}")


def source_refs(profile: dict) -> set[str]:
    refs: set[str] = set()
    for field in ("english_source", "latin_source", "lxx_source"):
        value = profile.get(field)
        if value:
            refs.add(str(value))
    for field in ("primary_text_source", "linguistic_source"):
        value = profile.get(field)
        if isinstance(value, list):
            refs.update(str(item) for item in value if item)
        elif value:
            refs.add(str(value))
    for segment in profile.get("segments") or []:
        value = segment.get("text_source")
        if value:
            refs.add(str(value))
    return refs


def main() -> int:
    sources_payload = load_json(SOURCES_PATH)
    books_payload = load_json(BOOKS_PATH)
    token_schema = load_json(TOKEN_SCHEMA_PATH)

    required_token_fields = {
        "id", "book_id", "chapter", "verse", "position", "language", "surface", "normalized",
        "lemma", "transliteration", "gloss", "part_of_speech", "morphology", "text_source", "linguistic_source",
    }
    if not required_token_fields.issubset(set(token_schema.get("required") or [])):
        fail("token schema is missing canonical required fields")

    sources = sources_payload.get("sources") or []
    if not sources:
        fail("source manifest is empty")
    source_ids = [str(row.get("id") or "").strip() for row in sources]
    if any(not source_id for source_id in source_ids) or len(set(source_ids)) != len(source_ids):
        fail("source ids must be non-empty and unique")
    source_index = dict(zip(source_ids, sources))

    for source_id, source in source_index.items():
        for field in ("title", "status", "rights"):
            if not str(source.get(field) or "").strip():
                fail(f"source {source_id} is missing {field}")
        allowed = source.get("production_import_allowed")
        if not isinstance(allowed, bool):
            fail(f"source {source_id} must declare production_import_allowed as boolean")
        if allowed:
            if source.get("license_verified") is not True:
                fail(f"production source {source_id} is not license-verified")
            if source.get("source_inventory_verified") is not True:
                fail(f"production source {source_id} does not have a verified source inventory")
            if not source.get("pin"):
                fail(f"production source {source_id} has no immutable pin")
            if not str(source.get("attribution") or "").strip():
                fail(f"production source {source_id} has no attribution record")
        if source.get("share_alike") is True and source.get("isolation_required") is not True:
            fail(f"ShareAlike source {source_id} must be isolated from non-SA corpus layers")
        if source.get("status", "").startswith("pending") and allowed:
            fail(f"pending source {source_id} cannot be production-importable")

    profiles = books_payload.get("profiles") or {}
    if not profiles:
        fail("book source profiles are missing")
    for profile_id, profile in profiles.items():
        if not profile.get("interlinear_strategy"):
            fail(f"profile {profile_id} is missing interlinear_strategy")
        if not profile.get("primary_interlinear_language"):
            fail(f"profile {profile_id} is missing primary_interlinear_language")
        for source_id in source_refs(profile):
            if source_id not in source_index:
                fail(f"profile {profile_id} references unknown source {source_id}")

    books = books_payload.get("books") or []
    if len(books) != 73 or int(books_payload.get("book_count") or 0) != 73:
        fail(f"Catholic canon mapping must contain exactly 73 books; found {len(books)}")
    orders = [row.get("order") for row in books]
    if orders != list(range(1, 74)):
        fail("book order must be exactly 1 through 73")
    ids = [str(row.get("id") or "") for row in books]
    names = [str(row.get("name") or "") for row in books]
    if len(set(ids)) != 73 or any(not item for item in ids):
        fail("book ids must be non-empty and unique")
    if len(set(names)) != 73 or any(not item for item in names):
        fail("book names must be non-empty and unique")
    for book in books:
        if book.get("testament") not in {"OT", "NT"}:
            fail(f"{book['name']} has invalid testament")
        if book.get("profile") not in profiles:
            fail(f"{book['name']} references unknown source profile {book.get('profile')}")

    if not DEUTEROCANON.issubset(set(names)):
        fail("deuterocanonical books are missing from the normal 73-book mapping")

    by_id = {row["id"]: row for row in books}
    if by_id["EST"]["profile"] != "esther-composite":
        fail("Esther must use the composite Hebrew/Greek profile")
    if by_id["DAN"]["profile"] != "daniel-composite":
        fail("Daniel must use the composite Hebrew/Aramaic/Greek profile")

    esther_segments = {row.get("name") for row in profiles["esther-composite"].get("segments") or []}
    if "Greek additions to Esther" not in esther_segments:
        fail("Esther must explicitly map the Greek additions")
    daniel_segments = {row.get("name") for row in profiles["daniel-composite"].get("segments") or []}
    if not REQUIRED_DANIEL_ADDITIONS.issubset(daniel_segments):
        fail("Daniel must explicitly map all Catholic Greek additions")
    for book_id in {"TOB", "JDT", "WIS", "SIR", "BAR", "1MA", "2MA"}:
        if by_id[book_id]["profile"] != "greek-deuterocanonical":
            fail(f"{by_id[book_id]['name']} must use the Greek deuterocanonical profile")

    lxx = source_index.get("first1kgreek-swete") or {}
    if lxx.get("status") != "approved-for-production-ingestion":
        fail("LXX must record accepted production-ingestion status")
    if lxx.get("production_import_allowed") is not True or lxx.get("source_inventory_verified") is not True:
        fail("LXX accepted Swete inventory must be production-importable")
    if lxx.get("share_alike") is not True or lxx.get("isolation_required") is not True:
        fail("LXX ShareAlike isolation gate is missing")
    acceptance = lxx.get("owner_acceptance") or {}
    if acceptance.get("phase") != "Old Testament Expansion Phase 1B" or acceptance.get("merge_commit") != PHASE1B_ACCEPTANCE_MERGE:
        fail("LXX exact-head owner acceptance is missing or changed")
    integrity = lxx.get("integrity") or {}
    if integrity.get("status") != "verified-by-phase1b-source-lock" or integrity.get("witness_count") != 15 or integrity.get("source_verse_record_count") != 5337:
        fail("LXX accepted deuterocanonical source-inventory integrity evidence is incomplete")
    full_scope = lxx.get("full_protocanonical_package") or {}
    if full_scope.get("book_scope_count") != 39 or full_scope.get("tree_sha") != "e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79":
        fail("full protocanonical Swete package pin is missing")

    vulgate = source_index.get("vulgate-clementine") or {}
    if vulgate.get("status") != "approved-for-production-ingestion" or vulgate.get("production_import_allowed") is not True:
        fail("Clementine Vulgate must be approved for production ingestion")
    if vulgate.get("rights") != "public-domain" or vulgate.get("license") != "Public Domain":
        fail("Clementine Vulgate public-domain rights record is missing")
    pin = vulgate.get("pin") or {}
    if pin.get("type") != "git-commit" or pin.get("value") != VULGATE_COMMIT:
        fail("Clementine Vulgate immutable source commit changed")
    integrity = vulgate.get("integrity") or {}
    if integrity.get("git_blob_sha1") != VULGATE_BLOB or integrity.get("rights_evidence_git_blob_sha1") != VULGATE_RIGHTS_BLOB:
        fail("Clementine Vulgate source/rights blob evidence changed")

    print(
        "Logos interlinear validation passed: "
        f"{len(books)} books, {len(profiles)} source profiles, {len(sources)} source records, "
        f"{sum(1 for source in sources if source.get('production_import_allowed'))} production-approved sources"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
