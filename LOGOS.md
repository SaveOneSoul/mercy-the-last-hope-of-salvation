# Logos — Biblical Study & Catholic Exegesis

Logos is the biblical-study section of **Mercy – The Last Hope of Salvation**.

## Public entry point

`/pages/logos.html`

## Current architecture

- GitHub Pages serves the responsive study shell.
- `javascript/logos.js` retrieves live study data from the Mercy Cloud Run API.
- `cloud-backend/app/logos.py` exposes the Logos API namespace.
- `cloud-backend/app/logos_seed.json` is the source-rights registry and deterministic seed corpus.
- Magisterium AI is invoked only through the server-side Mercy backend; no provider secret is exposed to GitHub Pages.

## API namespace

- `GET /api/logos/catalog`
- `GET /api/logos/source-rights`
- `GET /api/logos/passage?reference=John%201:1`
- `GET /api/logos/interlinear?reference=John%201:1`
- `GET /api/logos/commentary?reference=John%201:1`
- `GET /api/logos/fathers?reference=John%201:1`
- `GET /api/logos/preacher?reference=John%201:1`
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

The interface exposes study lanes for English, Hebrew, Latin, Aramaic/Syriac and Greek, but the UI must distinguish an original-language witness from a later translation.

- Hebrew/Aramaic are relevant to parts of the Old Testament.
- Greek is the principal original-language lane for the New Testament and is also relevant to Septuagint/deuterocanonical study.
- Latin is a historic ecclesial translation tradition rather than an original biblical language.
- English is a translation lane.
- Aramaic/Syriac editions must be provenance- and license-locked before a full corpus is imported.

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

## Implemented foundation

The current seed validates the complete 73-book Catholic canon metadata and provides working demonstration passages for `Genesis 1:1` and `John 1:1`, including parallel text lanes, interlinear tokens, Catholic exegetical notes, Father/Patristic source pointers, original preacher-outline scaffolds, biblical-place records, map support, licensed-media records and Magisterium AI themes.

The full Bible corpus is intentionally a separate ingestion milestone so source rights, edition provenance and checksums are established before mass publication.
