# Logos — Biblical Study & Catholic Exegesis

Logos is the biblical-study section of **Mercy – The Last Hope of Salvation**.

## Public entry point

`/pages/logos.html`

## Current architecture

- GitHub Pages serves the responsive study shell.
- `javascript/logos.js` retrieves live study data from the Mercy Cloud Run API.
- `cloud-backend/app/logos.py` exposes the core Logos API namespace.
- `cloud-backend/app/logos_advanced.py` exposes advanced background, chronology, commentary-tradition and advanced-AI routes.
- `cloud-backend/app/logos_context.py` contains deterministic testament/book context, evidence-class rules and external research-library metadata.
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

## Advanced study layers

Logos now exposes ten study tabs:

1. **Interlinear** — installed original-language tokens where a pinned dataset exists.
2. **Catholic Exegesis** — curated passage commentary plus Catholic hermeneutical framing.
3. **Fathers & Catena** — source-bounded patristic material and Catena pointers.
4. **Background & Audience** — historical/theological background for both Testaments plus a book-specific profile for every one of the 73 Catholic books, including audience/occasion cautions.
5. **History & Archaeology** — historical-place and archaeological context with explicit evidence limits.
6. **Chronology & Archives** — secular history, royal chronology, annals, inscriptions, coins and documentary evidence classified as direct attestation, synchronism, contextual evidence, disputed identification or reconstruction.
7. **Commentary Traditions** — Catholic, Jewish, Eastern Christian, Protestant/Evangelical and ecumenical/critical traditions shown distinctly rather than blended together.
8. **Preacher** — Catholic preaching scaffolds.
9. **Maps & Images** — licensed media and map orientation.
10. **Source Rights** — provenance and display-rights registry.

Book-level metadata is deterministic. Passage-level historical and theological conclusions remain text-sensitive: the AI layer must state when authorship, dating, destination, chronology or identification is traditional, probable, disputed or unknown.

## Secular history, kings, archives and chronology

When a passage is studied historically, Logos distinguishes:

- **direct external attestation** — a named person, ruler, place or event is independently attested;
- **chronological synchronism** — biblical and external dates/regnal systems can be compared with assumptions stated;
- **contextual evidence** — evidence illuminates the period without directly attesting the biblical event;
- **disputed identification** — a proposed site/person/inscription/date remains contested;
- **historical reconstruction** — a scholarly synthesis, not an archive fact.

Relevant evidence lenses include Assyrian royal inscriptions and eponym chronology, Babylonian Chronicles, Achaemenid/Persian evidence, Seleucid/Ptolemaic chronology, Roman imperial/provincial sources, inscriptions, coins, papyri and ancient historians where they genuinely apply. Archaeology or secular archives must never be represented as automatic proof of a theological claim.

## Catholic, Jewish and other Christian commentaries

Catholic doctrine and authoritative Catholic teaching remain clearly identified. Comparative material may include Jewish, Eastern Christian/Orthodox, Protestant/Evangelical and ecumenical historical-critical interpretation, but these are labeled as comparative context rather than silently merged into Catholic teaching.

For Jewish interpretation, Logos distinguishes ancient Jewish context from later rabbinic, medieval and modern Jewish interpretation. For other Christian traditions, doctrinal differences are named when material to the passage rather than caricatured or hidden.

## e-Catholic 2000 research-library integration

The following user-requested libraries are exposed as external research references in the **Commentary Traditions** layer:

- Catena Aurea by St. Thomas Aquinas;
- 1913 Catholic Encyclopedia;
- Summa Theologica;
- Ante-Nicene, Nicene and Post-Nicene Fathers;
- Library of Christian Classics;
- Catholic Church Documents;
- e-Catholic 2000 portal;
- The Great Commentary of Cornelius à Lapide.

The e-Catholic 2000 host currently displays an **all-rights-reserved** site notice on pages checked during implementation. Logos therefore links to those hosted resources but does not scrape or bundle their full hosted text. A future local import must use an independently verified reusable edition or written permission and must record author/work, edition/translator, provenance, license and checksum.

## API namespace

Core routes:

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

Advanced routes:

- `GET /api/logos/background?reference=Romans%201:1`
- `GET /api/logos/chronology?reference=2%20Kings%2018:13`
- `GET /api/logos/traditions?reference=John%206:51`
- `POST /api/logos/advanced-ai`

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
3. historical reconstruction;
4. secular historical or archaeological evidence;
5. Jewish interpretive context;
6. patristic/Catholic tradition;
7. Magisterial teaching;
8. other Christian commentary traditions;
9. modern scholarship;
10. AI synthesis.

AI must not fabricate manuscript readings, royal-annal entries, inscriptions, archaeological discoveries, Father quotations, commentary quotations, page numbers or citations. If evidence is insufficient or disputed, it must say so.

## Rebuilding the corpus

Run:

```bash
python scripts/vendor_douay_rheims.py
```

The dedicated GitHub Action performs the same deterministic import and commits regenerated corpus files only after all integrity gates pass.
