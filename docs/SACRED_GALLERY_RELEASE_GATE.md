# Sacred Gallery — Editorial and Release Gate

Status: **HOLD — not ready to merge**. Review date: 2026-10-14.

## Theological review
- All 51 Marian invocation labels have corresponding meaning, biblical reference, and historical-context entries in `pages/gallery.html`.
- These entries are concise editorial summaries, **not** a completed source-by-source doctrinal audit.
- Distinguish dogma (Theotokos, Immaculate Conception, Assumption), liturgical/devotional titles, and typological readings (Ark, Towers, Rose, Morning Star).
- Verify historical statements (Council of Ephesus 431, 1854/1950 definitions, title additions in 1964/1980/1995) against Vatican primary documents before acceptance.
- Confirm Litany text/version, including later additions, without silently modifying the owner's 51-title collection.

## Artwork audit
- Four proposed Commons file paths are stored as `candidateArt` for future investigation; `approvedArt` is intentionally empty.
- For every image, verify that the exact file exists, the depicted subject matches the invocation, creator/title/date are accurate, licence/public-domain rationale applies in relevant jurisdictions, attribution and source are recorded, and the image loads.
- AI-generated poster concepts are not individually licensed historical artworks and should not be described as such.
- Do not publish candidate art until verification is complete.

## Accessibility and browser checks
- Inspect on desktop and mobile: keyboard navigation, filter and search controls, focus trapping/return from dialog, Escape close, contrast, alt text, and reduced-motion preferences.
- The dialog has a fallback for browsers without native showModal/close support, but the fallback requires manual keyboard/focus testing.
- Run automated HTML/JS linting and an axe-core or equivalent accessibility scan, then record results.
- Confirm that gallery navigation works from GitHub Pages project subpath.

## Release decision
- Draft PR #159 remains unmerged. No production deployment or owner merge approval requested until image provenance, theological citations, and accessibility checks are complete.

## Review update — 2026-10-14
- Official Vatican Litany checked: the 2020 additions Mother of Mercy, Mother of Hope, and Solace of Migrants have been inserted in the correct sequence. Gallery now contains 54 Marian invocations with 54 corresponding notes.
- The original owner's 51 titles remain preserved. Differences in English translation (for example Comforter/Comfort of the afflicted and honor/honour) are retained as provided rather than silently rewritten.
- Wikimedia Commons exact file record confirmed for Raphael's *Virgin and Child with Young Saint John the Baptist* (MFA Boston accession 76.422), with Commons PD-Art statement and jurisdictional caveat.
- Other image files require separate exact-record and live-image checks; no claim of complete verification.
- Static source inspection confirms search, category filters, dialog, Escape support via native dialog, and focus return handlers exist. Browser automation, screen reader testing, contrast audit, and mobile checks remain NOT RUN.
- Editorial check remains incomplete for 54 individual theological/historical claims. The Litany source confirms titles but not every individual interpretation or date.
- Release decision remains HOLD; draft PR only.

## Verification checkpoint — 2026-10-14 (follow-up)
- Cross-checked the complete Litany order and 2020 placements against https://press.vatican.va/special/rosary/documents/litanie-lauretane_en.html and the 20 June 2020 Vatican letter https://press.vatican.va/content/salastampa/en/bollettino/pubblico/2020/06/20/200620c.html.
- Confirmed the Raphael *Virgin and Child with Young Saint John the Baptist* file metadata on Wikimedia Commons, accession MFA Boston 76.422: https://commons.wikimedia.org/wiki/File:Raphael_(Raffaello_Sanzio_or_Santi)_-_Virgin_and_Child_with_Young_Saint_John_the_Baptist_-_76.422_-_Museum_of_Fine_Arts.jpg. Public-domain marking carries jurisdiction-specific caveats.
- Tightened gallery's published approved-art manifest to this one directly verified artwork; remaining candidate artwork is unpublished pending exact file record checks.
- Source-inspected all 54 title/note keys for completeness and checked that dialog labeling, live count announcements, search event wiring and focus-return code exist. This is NOT a browser-based accessibility test.
- Added `scripts/check-sacred-gallery.cjs` static regression test; the workflow creation attempt was blocked, so no CI result exists for it. The script itself has not been executed on a runner.
- Open gates: 53 additional distinct Marian artwork selections and licence verification (plus non-Marian sections); individual theological and historical source substantiation; cross-browser/mobile/assistive-technology audit; successful test execution; review of the proposed image selection against Catholic iconographic suitability.
- Decision: **DO NOT MERGE OR PUBLISH**; keep PR #159 draft until all requirements are satisfied and owner approval is obtained.

## Follow-up checkpoint — artwork verification and structural audit
- Exact Commons file pages independently checked for Murillo's *The Immaculate Conception* (Dayton Art Institute) and Velázquez's *Coronation of the Virgin* (Museo del Prado). Both have public-domain artwork/reproduction notices; jurisdictional caveats apply. Their candidate records were enabled in the gallery.
- Gallery approved artwork total: **3** (including previously reviewed Raphael). This is not 54 distinct verified Marian images.
- In-memory parse of the committed gallery data confirms 54 Marian titles, 54 note objects, 0 entries with missing required fields. This validates completeness, not factual accuracy.
- Primary source for Litany sequence: https://www.vatican.va/special/rosary/documents/litanie-lauretane_en.html
- Murillo provenance: https://commons.wikimedia.org/wiki/File:'The_Immaculate_Conception'_by_Murillo,_Dayton_Art_Institute.JPG
- Velázquez provenance: https://commons.wikimedia.org/wiki/File:Coronación_de_la_Virgen,_by_Diego_Velázquez.jpg
- Still blocked: remaining unique artwork and iconographic fit, exhaustive 54-entry primary-source review, executable CI and browser accessibility tests. No release approval.
