# Logos — Complete Old Testament Original-Language Production Contract

This milestone completes the repository-side architecture for a unified Catholic Old Testament study view while preserving independent source, rights and versification boundaries.

## Primary Catholic Bible lane

The installed **Douay-Rheims 1899** 73-book English corpus remains the primary public Catholic Bible text. Original-language witnesses are study layers and never replace the English corpus.

## Hebrew and Biblical Aramaic

Production corpus: `heb_arc_oshb_wlc`

- 39 Masoretic/Hebrew-Bible witnesses used within the Catholic Old Testament
- Westminster Leningrad Codex source-script surface: Public Domain
- Open Scriptures Hebrew Bible lemma/morphology/source-word annotations: CC BY 4.0
- Hebrew/Aramaic Unicode preserved verbatim
- no fabricated gloss or transliteration
- Douay-Rheims alignment must pass an explicit chapter map where required and exact numeric verse-identity validation before serving
- simple whole-Psalm Vulgate/LXX-to-MT numbering shifts are explicitly mapped; split/combined Psalm loci remain blocked until segment-level mappings are reviewed

## Septuagint Greek

Two complementary production packages preserve the accepted witness architecture.

### Protocanonical complement

Production corpus: `grc_ot_swete_protocanonical`

- 37 Catholic OT books not supplied by the accepted deuterocanonical/Esther/Daniel package
- pinned OpenGreekAndLatin First1KGreek Swete tree
- source commit `8ee111eb44ecef4120c844e10749178d95d1f30c`
- source tree `e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79`
- CC BY-SA 4.0 isolated partition
- source Greek boundaries preserved
- Esdras B is explicitly partitioned as source chapters 1–10 => Ezra 1–10 and source chapters 11–23 => Nehemiah 1–13
- no gloss, lemma, morphology or transliteration is invented
- chapters are served only when numeric Douay-Rheims/source verse identities match exactly

### Accepted Catholic Greek/deuterocanonical package

Production corpus: `grc_ot_catholic_swete`

The existing accepted package remains unchanged for Esther, Judith, Tobit, 1–2 Maccabees, Wisdom, Sirach, Baruch/Letter of Jeremiah and Daniel, including Theodotion/Old Greek parallel-witness boundaries and component-range mappings.

Together the two Greek packages cover the 46-book Catholic Old Testament scope without flattening accepted witness differences.

## Latin

Production corpus: `lat_clementine_vulgate`

- edition: **Biblia Sacra juxta Vulgatam Clementinam** / Sixto-Clementine Vulgate
- pinned mirror: `jrichter/ClementineVulgateConverter`
- commit `38292f3f91e874d3db9e7e9bf7abd23da3217054`
- source artifact `lat-clementine-vul.usfx.xml`
- Git blob `a9ec3099e8f641d601679242354366aff150070e`
- source text declared Public Domain by The Clementine Vulgate Project
- converter/mirror code license is separate from text rights
- full 73-book Catholic canon must match the installed Douay-Rheims book-id set
- no Latin gloss, lemma, morphology or transliteration is fabricated
- chapters are served only after exact numeric Douay-Rheims/source verse-identity verification

## Unified frontend

The normal **Interlinear** tab is the single entry point.

For Old Testament references it requests, independently:

1. Douay-Rheims English passage
2. WLC/OSHB Hebrew/Aramaic study layer
3. protocanonical Swete Septuagint layer
4. accepted Catholic Greek/deuterocanonical layer where applicable
5. Clementine Latin Vulgate layer

A failed or unmapped source layer does not hide the other verified layers. A versification mismatch is displayed as a mapping-required condition; the frontend does not silently renumber Scripture.

For New Testament references the existing production SBLGNT/MorphGNT Interlinear path remains unchanged.

## Release gates

Repository acceptance requires:

- deterministic source locks and integrity digests
- corpus validators for all generated packages
- backend route smoke tests
- JavaScript syntax checks and unified frontend contract validation
- project-owner acceptance at the exact reviewed PR head
- squash merge
- successful post-merge corpus generation on `main`
- Cloud Run deployment of the generated `main` state
- live checks for Genesis 1 / Genesis 1:1 across Hebrew/Aramaic, Septuagint and Vulgate endpoints before declaring the production backend complete
- successful GitHub Pages deployment before declaring the unified frontend live

Repository implementation is not equivalent to Cloud Run deployment. Live status must be verified separately after the generated corpora exist on `main`.
