# Logos — Biblical Study & Catholic Exegesis

Logos is the biblical-study section of **Mercy – The Last Hope of Salvation**.

## Public entry point

`/pages/logos.html`

## Current architecture

- GitHub Pages serves the responsive study shell.
- `javascript/logos.js` retrieves live study data from the Mercy Cloud Run API.
- `cloud-backend/app/logos.py` exposes the Logos API namespace.
- `cloud-backend/app/logos_seed.json` remains the source-rights registry and curated parallel/interlinear study seed.
- `cloud-backend/app/logos_corpus/eng_douay_rheims_1899/` contains the vendored full English Catholic Bible corpus.
- `scripts/vendor_douay_rheims.py` reproduces the corpus from the pinned source and verifies source integrity and the 73-book canon.
- Magisterium AI is invoked only through the server-side Mercy backend; no provider secret is exposed to GitHub Pages.

## Full English Catholic corpus

The production English Scripture lane is the **Douay-Rheims American Edition (1899)**, a public-domain Catholic Bible containing the full 73-book canon.

The corpus is vendored into the repository rather than fetched at runtime. The importer is source-locked to the eBible `engDRA` USFM data mirrored in `gracious-tech/fetch_collection` at commit `772e1ab2b13af88cde05237fb9a8218cee9261bb`. Before extraction it verifies the source ZIP against Git blob SHA-1 `b02336cd5db942f8ce6a2cede902f1b4d4927896`; the generated manifest also records the downloaded ZIP SHA-256.

The ingestion gate requires:

- exactly 73 canonical Catholic books;
- a complete expected USFM book-code set, including Tobit, Judith, Wisdom, Sirach, Baruch and 1–2 Maccabees;
- more than 1,300 chapters and 34,000 verse records;
- representative integrity checks across the Old Testament, deuterocanonical books and New Testament;
- one deterministic JSON file per book plus `manifest.json`.

The API accepts canonical names and common abbreviations and can resolve a chapter, a single verse or a short same-chapter range, for example `Genesis 10:10`, `John 3:16-18`, `Tobit 4` and `2 Maccabees 7:9`.

## API namespace

- `GET /api/logos/catalog`
- `GET /api/logos/source-rights`
- `GET /api/logos/passage?reference=John%203:16`
- `GET /api/logos/interlinear?reference=John%201:1`
- `GET /api/logos/commentary?reference=John%203:16`
- `GET /api/logos/fathers?reference=John%203:16`
- `GET /api/logos/preacher?reference=John%203:16`
- `GET /api/logos/places?reference=Luke%202`
- `GET /api/logos/media`
- `POST /api/logos/ai`

## Source-rights policy

The project does **not** treat all biblical or commentary data found online as reusable.

Every corpus source must record:

- title;
- author/editor where applicable;
- edition;
- language;
- provenance URL;
- copyright/license status;
- allowed display scope;
- pinned checksum/version before production import.

Public-domain or explicitly licensed sources may be imported after provenance locking. Modern copyrighted works, including the Jerome Biblical Commentary, remain bibliographic/reference-only unless permission or a suitable license permits full-text display.

## Original-language policy

The interface exposes study lanes for English, Hebrew, Latin, Aramaic/Syriac and Greek, but the UI distinguishes an original-language witness from a later translation.

- The full **English** 73-book corpus is installed.
- Hebrew/Aramaic are relevant to parts of the Old Testament, but their full digital corpus remains edition/license gated.
- Greek is the principal original-language lane for the New Testament and is also relevant to Septuagint/deuterocanonical study; full bulk ingestion remains provenance gated.
- Latin is a historic ecclesial translation tradition rather than an original biblical language; its complete corpus is a later ingestion milestone.
- Aramaic/Syriac editions must be provenance- and license-locked before a full corpus is imported.

The curated Genesis 1:1 and John 1:1 records continue to demonstrate parallel-language and interlinear functionality while the original-language corpora are independently approved.

## AI policy

Magisterium AI may explain, compare and synthesize, but must keep these categories distinct:

1. biblical text;
2. lexical/grammatical observation;
3. historical or archaeological evidence;
4. patristic interpretation;
5. Magisterial teaching;
6. modern scholarship;
7. AI synthesis.

AI must not fabricate manuscript readings, archaeological discoveries, Father quotations, commentary quotations, page numbers or citations.

## Rebuilding the corpus

Run:

```bash
python scripts/vendor_douay_rheims.py
```

The dedicated GitHub Action performs the same deterministic import and commits regenerated corpus files only after all integrity gates pass.
