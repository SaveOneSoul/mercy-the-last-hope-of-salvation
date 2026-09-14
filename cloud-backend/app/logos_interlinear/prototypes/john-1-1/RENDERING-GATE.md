# Rendering gate

The prototype renderer must load the published canonical JSON rather than duplicate the verse data in JavaScript or HTML.

Acceptance criteria:

- `JHN-1-1.json` loads successfully from the GitHub Pages data path.
- Exactly 17 tokens render in positions 1 through 17.
- Greek surface, transliteration, gloss, lemma, part of speech and morphology are visible without injecting source data through `innerHTML`.
- Field provenance and pinned source records are displayed.
- Mobile layout remains readable at narrow widths.
- The full-NT scaling gate remains locked.

CI validates the deterministic wiring. A browser check of the deployed page completes the rendering acceptance gate.
