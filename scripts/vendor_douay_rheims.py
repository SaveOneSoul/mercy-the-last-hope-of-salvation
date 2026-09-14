#!/usr/bin/env python3
"""Vendor the full public-domain Douay-Rheims 1899 Catholic Bible corpus.

The importer is intentionally deterministic and source-locked:
- source: gracious-tech/fetch_collection mirror of eBible engDRA USFM
- source repository commit is pinned
- source ZIP Git blob SHA-1 is verified before extraction
- exactly the 73 canonical Catholic books must be present
- generated output is stable JSON, one file per book plus a manifest

No network access is required at runtime. The generated corpus is committed into
``cloud-backend/app/logos_corpus/eng_douay_rheims_1899`` and Cloud Run reads it
locally.
"""

from __future__ import annotations

import hashlib
import io
import json
import re
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "cloud-backend" / "app" / "logos_corpus" / "eng_douay_rheims_1899"

SOURCE_REPOSITORY = "gracious-tech/fetch_collection"
SOURCE_COMMIT = "772e1ab2b13af88cde05237fb9a8218cee9261bb"
SOURCE_PATH = "bibles/eng_drae/source.zip"
SOURCE_URL = (
    "https://raw.githubusercontent.com/"
    f"{SOURCE_REPOSITORY}/{SOURCE_COMMIT}/{SOURCE_PATH}"
)
SOURCE_GIT_BLOB_SHA1 = "b02336cd5db942f8ce6a2cede902f1b4d4927896"
UPSTREAM_URL = "https://ebible.org/Scriptures/engDRA_usfm.zip"
RIGHTS_URL = "https://ebible.org/details.php?all=1&id=engDRA"

BOOKS = [
    ("GEN", "Genesis", "OT", ["gen", "ge", "gn"]),
    ("EXO", "Exodus", "OT", ["exo", "ex"]),
    ("LEV", "Leviticus", "OT", ["lev", "lv"]),
    ("NUM", "Numbers", "OT", ["num", "nm", "nb"]),
    ("DEU", "Deuteronomy", "OT", ["deu", "deut", "dt"]),
    ("JOS", "Joshua", "OT", ["jos", "josh"]),
    ("JDG", "Judges", "OT", ["jdg", "judg", "jgs"]),
    ("RUT", "Ruth", "OT", ["rut", "ruth"]),
    ("1SA", "1 Samuel", "OT", ["1 samuel", "1 sam", "1sa", "i samuel", "i sam"]),
    ("2SA", "2 Samuel", "OT", ["2 samuel", "2 sam", "2sa", "ii samuel", "ii sam"]),
    ("1KI", "1 Kings", "OT", ["1 kings", "1 king", "1 kgs", "1ki", "i kings"]),
    ("2KI", "2 Kings", "OT", ["2 kings", "2 king", "2 kgs", "2ki", "ii kings"]),
    ("1CH", "1 Chronicles", "OT", ["1 chronicles", "1 chron", "1 chr", "1ch", "i chronicles"]),
    ("2CH", "2 Chronicles", "OT", ["2 chronicles", "2 chron", "2 chr", "2ch", "ii chronicles"]),
    ("EZR", "Ezra", "OT", ["ezr", "ezra"]),
    ("NEH", "Nehemiah", "OT", ["neh", "nehemiah"]),
    ("TOB", "Tobit", "OT", ["tob", "tobit", "tobias"]),
    ("JDT", "Judith", "OT", ["jdt", "judith"]),
    ("EST", "Esther", "OT", ["est", "esth", "esther"]),
    ("1MA", "1 Maccabees", "OT", ["1 maccabees", "1 macc", "1 mac", "1ma", "i maccabees"]),
    ("2MA", "2 Maccabees", "OT", ["2 maccabees", "2 macc", "2 mac", "2ma", "ii maccabees"]),
    ("JOB", "Job", "OT", ["job"]),
    ("PSA", "Psalms", "OT", ["psa", "psalm", "psalms", "ps"]),
    ("PRO", "Proverbs", "OT", ["pro", "prov", "prv", "proverbs"]),
    ("ECC", "Ecclesiastes", "OT", ["ecc", "eccl", "ecclesiastes", "qoheleth"]),
    ("SNG", "Song of Songs", "OT", ["sng", "song", "song of songs", "song of solomon", "canticles", "canticle of canticles"]),
    ("WIS", "Wisdom", "OT", ["wis", "wisdom", "wisdom of solomon"]),
    ("SIR", "Sirach", "OT", ["sir", "sirach", "ecclesiasticus"]),
    ("ISA", "Isaiah", "OT", ["isa", "is", "isaiah"]),
    ("JER", "Jeremiah", "OT", ["jer", "jeremiah"]),
    ("LAM", "Lamentations", "OT", ["lam", "lamentations"]),
    ("BAR", "Baruch", "OT", ["bar", "baruch"]),
    ("EZK", "Ezekiel", "OT", ["ezk", "eze", "ezek", "ezekiel"]),
    ("DAN", "Daniel", "OT", ["dan", "dn", "daniel"]),
    ("HOS", "Hosea", "OT", ["hos", "hosea", "osee"]),
    ("JOL", "Joel", "OT", ["jol", "joel"]),
    ("AMO", "Amos", "OT", ["amo", "amos"]),
    ("OBA", "Obadiah", "OT", ["oba", "obad", "obadiah", "abdias"]),
    ("JON", "Jonah", "OT", ["jon", "jonah", "jonas"]),
    ("MIC", "Micah", "OT", ["mic", "micah", "micheas"]),
    ("NAM", "Nahum", "OT", ["nam", "nah", "nahum"]),
    ("HAB", "Habakkuk", "OT", ["hab", "habakkuk", "habacuc"]),
    ("ZEP", "Zephaniah", "OT", ["zep", "zeph", "zephaniah", "sophonias"]),
    ("HAG", "Haggai", "OT", ["hag", "haggai", "aggeus"]),
    ("ZEC", "Zechariah", "OT", ["zec", "zech", "zechariah", "zacharias"]),
    ("MAL", "Malachi", "OT", ["mal", "malachi", "malachias"]),
    ("MAT", "Matthew", "NT", ["mat", "matt", "mt", "matthew"]),
    ("MRK", "Mark", "NT", ["mrk", "mark", "mk"]),
    ("LUK", "Luke", "NT", ["luk", "luke", "lk"]),
    ("JHN", "John", "NT", ["jhn", "john", "jn"]),
    ("ACT", "Acts", "NT", ["act", "acts", "acts of the apostles"]),
    ("ROM", "Romans", "NT", ["rom", "romans", "rm"]),
    ("1CO", "1 Corinthians", "NT", ["1 corinthians", "1 cor", "1co", "i corinthians"]),
    ("2CO", "2 Corinthians", "NT", ["2 corinthians", "2 cor", "2co", "ii corinthians"]),
    ("GAL", "Galatians", "NT", ["gal", "galatians"]),
    ("EPH", "Ephesians", "NT", ["eph", "ephesians"]),
    ("PHP", "Philippians", "NT", ["php", "phil", "philippians"]),
    ("COL", "Colossians", "NT", ["col", "colossians"]),
    ("1TH", "1 Thessalonians", "NT", ["1 thessalonians", "1 thess", "1 thes", "1th"]),
    ("2TH", "2 Thessalonians", "NT", ["2 thessalonians", "2 thess", "2 thes", "2th"]),
    ("1TI", "1 Timothy", "NT", ["1 timothy", "1 tim", "1ti"]),
    ("2TI", "2 Timothy", "NT", ["2 timothy", "2 tim", "2ti"]),
    ("TIT", "Titus", "NT", ["tit", "titus"]),
    ("PHM", "Philemon", "NT", ["phm", "philemon"]),
    ("HEB", "Hebrews", "NT", ["heb", "hebrews"]),
    ("JAS", "James", "NT", ["jas", "james", "jam"]),
    ("1PE", "1 Peter", "NT", ["1 peter", "1 pet", "1 pe", "1pe"]),
    ("2PE", "2 Peter", "NT", ["2 peter", "2 pet", "2 pe", "2pe"]),
    ("1JN", "1 John", "NT", ["1 john", "1 jn", "1jn"]),
    ("2JN", "2 John", "NT", ["2 john", "2 jn", "2jn"]),
    ("3JN", "3 John", "NT", ["3 john", "3 jn", "3jn"]),
    ("JUD", "Jude", "NT", ["jud", "jude"]),
    ("REV", "Revelation", "NT", ["rev", "revelation", "apocalypse"]),
]

BOOK_BY_ID = {row[0]: row for row in BOOKS}
EXPECTED_IDS = set(BOOK_BY_ID)

FOOTNOTE_RE = re.compile(r"\\f\b.*?\\f\*", re.DOTALL)
XREF_RE = re.compile(r"\\x\b.*?\\x\*", re.DOTALL)
WORD_RE = re.compile(r"\\w\s+([^|\\]+?)(?:\|[^\\]*?)?\\w\*")
ATTR_RE = re.compile(r"\|[A-Za-z0-9_-]+=(?:\"[^\"]*\"|'[^']*'|[^\\\s]+)")
MARKER_RE = re.compile(r"\\\+?[A-Za-z0-9][A-Za-z0-9-]*\*?\s*")
SPACE_RE = re.compile(r"\s+")


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def download_source() -> bytes:
    request = urllib.request.Request(
        SOURCE_URL,
        headers={"User-Agent": "Mercy-Logos-Corpus-Importer/1.0"},
    )
    with urllib.request.urlopen(request, timeout=120) as response:
        data = response.read()
    actual = git_blob_sha1(data)
    if actual != SOURCE_GIT_BLOB_SHA1:
        raise RuntimeError(
            f"Source integrity failure: expected Git blob {SOURCE_GIT_BLOB_SHA1}, got {actual}"
        )
    return data


def clean_verse_text(raw: str) -> str:
    text = FOOTNOTE_RE.sub("", raw)
    text = XREF_RE.sub("", text)
    text = WORD_RE.sub(lambda match: match.group(1), text)
    text = ATTR_RE.sub("", text)
    text = MARKER_RE.sub("", text)
    text = text.replace("~", " ")
    return SPACE_RE.sub(" ", text).strip()


def parse_usfm(text: str) -> tuple[str, dict[str, dict[str, str]]]:
    book_id = ""
    chapter: str | None = None
    chapters: dict[str, dict[str, str]] = {}
    current_verse: str | None = None

    for raw_line in text.splitlines():
        line = raw_line.strip("\ufeff\r\n")
        if not line:
            continue
        if line.startswith("\\id "):
            book_id = line[4:].strip().split()[0].upper()
            continue
        if line.startswith("\\c "):
            match = re.match(r"\\c\s+(\d+)", line)
            if not match:
                raise RuntimeError(f"Invalid chapter marker in {book_id or 'unknown'}: {line!r}")
            chapter = str(int(match.group(1)))
            chapters.setdefault(chapter, {})
            current_verse = None
            continue
        if line.startswith("\\v "):
            if chapter is None:
                raise RuntimeError(f"Verse before chapter in {book_id or 'unknown'}")
            match = re.match(r"\\v\s+([0-9]+(?:[-,][0-9]+)?)\s*(.*)", line)
            if not match:
                raise RuntimeError(f"Invalid verse marker in {book_id}: {line[:80]!r}")
            verse_id = match.group(1)
            # The corpus normally uses integer verse ids. Preserve a bridge under
            # its literal id while also allowing the first verse number to resolve.
            current_verse = verse_id
            cleaned = clean_verse_text(match.group(2))
            chapters[chapter][verse_id] = cleaned
            continue

        # eBible's engDRA export keeps verse text on the verse line. If a future
        # pinned source introduces explicit continuation paragraph/poetry lines,
        # append only semantic text markers, never section headings or metadata.
        if current_verse and line.startswith(("\\q", "\\m", "\\p", "\\nb", "\\li")):
            continuation = re.sub(r"^\\[A-Za-z0-9+-]+\s*", "", line)
            continuation = clean_verse_text(continuation)
            if continuation:
                prior = chapters[chapter][current_verse]
                chapters[chapter][current_verse] = (prior + " " + continuation).strip()

    if not book_id:
        raise RuntimeError("USFM file has no \\id marker")
    if not chapters:
        raise RuntimeError(f"USFM book {book_id} has no chapters")
    return book_id, chapters


def locate_usfm_files(archive: zipfile.ZipFile) -> list[str]:
    candidates = []
    for name in archive.namelist():
        lower = name.lower()
        if lower.endswith((".usfm", ".sfm")) and not name.endswith("/"):
            candidates.append(name)
    if not candidates:
        raise RuntimeError("Source ZIP contained no USFM files")
    return sorted(candidates)


def ensure_clean_output() -> None:
    if OUT_DIR.exists():
        shutil.rmtree(OUT_DIR)
    OUT_DIR.mkdir(parents=True, exist_ok=True)


def stable_dump(path: Path, payload: dict) -> None:
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def validate_generated(manifest: dict) -> None:
    if manifest["book_count"] != 73:
        raise RuntimeError(f"Expected 73 books, got {manifest['book_count']}")
    ids = {row["id"] for row in manifest["books"]}
    if ids != EXPECTED_IDS:
        missing = sorted(EXPECTED_IDS - ids)
        extra = sorted(ids - EXPECTED_IDS)
        raise RuntimeError(f"Canon mismatch; missing={missing}, extra={extra}")
    if manifest["chapter_count"] < 1300:
        raise RuntimeError(f"Unexpectedly low chapter count: {manifest['chapter_count']}")
    if manifest["verse_count"] < 34000:
        raise RuntimeError(f"Unexpectedly low verse count: {manifest['verse_count']}")

    required = [
        ("GEN", "1", "1"),
        ("TOB", "1", "1"),
        ("WIS", "1", "1"),
        ("SIR", "1", "1"),
        ("1MA", "1", "1"),
        ("2MA", "1", "1"),
        ("MAT", "1", "1"),
        ("JHN", "3", "16"),
        ("REV", "22", "21"),
    ]
    for book_id, chapter, verse in required:
        book = json.loads((OUT_DIR / f"{book_id.lower()}.json").read_text(encoding="utf-8"))
        text = ((book.get("chapters") or {}).get(chapter) or {}).get(verse)
        if not text:
            raise RuntimeError(f"Required verse missing: {book_id} {chapter}:{verse}")


def main() -> int:
    source_bytes = download_source()
    source_sha256 = hashlib.sha256(source_bytes).hexdigest()
    ensure_clean_output()

    parsed: dict[str, dict[str, dict[str, str]]] = {}
    with zipfile.ZipFile(io.BytesIO(source_bytes)) as archive:
        for member in locate_usfm_files(archive):
            text = archive.read(member).decode("utf-8-sig")
            book_id, chapters = parse_usfm(text)
            if book_id in EXPECTED_IDS:
                if book_id in parsed:
                    raise RuntimeError(f"Duplicate canonical book in source: {book_id}")
                parsed[book_id] = chapters

    if set(parsed) != EXPECTED_IDS:
        missing = sorted(EXPECTED_IDS - set(parsed))
        extra = sorted(set(parsed) - EXPECTED_IDS)
        raise RuntimeError(f"Source canon mismatch; missing={missing}, extra={extra}")

    manifest_books = []
    total_chapters = 0
    total_verses = 0

    for book_id, canonical_name, testament, aliases in BOOKS:
        chapters = parsed[book_id]
        chapter_count = len(chapters)
        verse_count = sum(len(verses) for verses in chapters.values())
        total_chapters += chapter_count
        total_verses += verse_count
        filename = f"{book_id.lower()}.json"
        payload = {
            "id": book_id,
            "name": canonical_name,
            "testament": testament,
            "translation": "Douay-Rheims American Edition (1899)",
            "source_id": "drb-challoner",
            "chapters": chapters,
        }
        stable_dump(OUT_DIR / filename, payload)
        manifest_books.append(
            {
                "id": book_id,
                "name": canonical_name,
                "testament": testament,
                "filename": filename,
                "chapter_count": chapter_count,
                "verse_count": verse_count,
                "aliases": aliases,
            }
        )

    manifest = {
        "schema_version": 1,
        "corpus_version": "2026.09.14-douay-rheims-1899-full-73",
        "translation": {
            "id": "drb-challoner",
            "title": "Douay-Rheims American Edition (1899)",
            "language": "en",
            "canon": "Catholic 73-book canon",
            "rights": "public-domain",
            "allowed_display_scope": "full-text",
            "upstream_rights_url": RIGHTS_URL,
        },
        "source": {
            "upstream": "eBible.org engDRA USFM",
            "upstream_url": UPSTREAM_URL,
            "mirror_repository": SOURCE_REPOSITORY,
            "mirror_commit": SOURCE_COMMIT,
            "mirror_path": SOURCE_PATH,
            "download_url": SOURCE_URL,
            "git_blob_sha1": SOURCE_GIT_BLOB_SHA1,
            "download_sha256": source_sha256,
            "integrity": "verified",
        },
        "book_count": len(manifest_books),
        "chapter_count": total_chapters,
        "verse_count": total_verses,
        "books": manifest_books,
    }
    stable_dump(OUT_DIR / "manifest.json", manifest)
    validate_generated(manifest)

    print(
        "Vendored Douay-Rheims corpus: "
        f"{manifest['book_count']} books, {total_chapters} chapters, {total_verses} verse records"
    )
    print(f"Source SHA-256: {source_sha256}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - command-line failure path
        print(f"ERROR: {exc}", file=sys.stderr)
        raise
