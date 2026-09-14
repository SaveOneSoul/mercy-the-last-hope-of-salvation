# Logos Interlinear Corpus Foundation

This directory is the provenance and schema gate for original-language interlinear data used by Logos.

It does **not** contain a bulk Hebrew, Greek, Septuagint, or Latin corpus yet. A source may be mapped to Catholic books before it is importable, but `sources-manifest.json` is authoritative: sources with `production_import_allowed: false` must not be bulk imported or rendered as installed corpus data.

## Files

- `sources-manifest.json` — licence, provenance, immutable pins, attribution, import status, and ShareAlike isolation policy.
- `books.json` — source-language and source-dataset mapping for the normal 73-book Catholic canon.
- `token.schema.json` — canonical word-token contract for future importers.
- `NOTICE.md` — attribution and rights notes for sources already verified at the foundation gate.

## Rendering policy

Canonical interlinear data is structured JSON/database data. The live website should render it as semantic HTML/CSS so text remains searchable, selectable, accessible, responsive, and usable with Hebrew right-to-left layout.

SVG is a **derived export format** for printing, sharing, or embedding. SVG files must not become the canonical Scripture/interlinear database.

## Canonical token contract

Future importers normalize source records to a shape such as:

```json
{
  "id": "JHN-1-1-GR-005",
  "book_id": "JHN",
  "chapter": 1,
  "verse": "1",
  "position": 5,
  "language": "grc",
  "surface": "λόγος",
  "normalized": "λόγος",
  "lemma": "λόγος",
  "transliteration": "logos",
  "gloss": "word",
  "part_of_speech": "noun",
  "morphology": "N-NSM",
  "text_source": "sblgnt",
  "linguistic_source": "stepbible-data"
}
```

`surface` must preserve the source text. Normalization, transliteration, glosses, and morphology are separate layers and must never overwrite the source form.

## Current source gates

The foundation currently permits future vendor pipelines for:

- Open Scriptures Hebrew Bible / WLC + OSHB annotations.
- SBL Greek New Testament.
- Published STEPBible datasets explicitly listed in `sources-manifest.json`.

The First1KGreek repository licence and immutable commit are recorded, but Septuagint import remains blocked until the exact Swete work/file inventory is pinned and checked. The Clementine Vulgate also remains blocked until one specific reusable digital transcription and checksum are pinned. WEB Catholic is only a candidate optional English lane; the installed Douay-Rheims corpus remains the production English text.

## Catholic canon rules

Deuterocanonical books are first-class books in `books.json`, not an appendix. Greek additions to Esther and Daniel are represented explicitly. Daniel preserves Hebrew, Aramaic, and Greek source-language segments rather than flattening them into one language lane.

Run:

```bash
python tools/validate_logos_interlinear.py
```

before changing source rights, book mappings, or future interlinear vendor scripts.
