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
