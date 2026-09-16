# Logos Old Testament Hebrew/Aramaic Production Integration

This milestone promotes the already accepted **Old Testament Expansion Phase 1A** OSHB/WLC evidence into a production package without changing the accepted source extraction rules.

## Production corpus

- Corpus id: `heb_arc_oshb_wlc`
- Corpus version: `2026.09.16-oshb-wlc-39`
- Source: Open Scriptures Hebrew Bible (`openscriptures/morphhb`)
- Source commit: `3d15126fb1ef74867fc1434be1942e837932691f`
- Locked `wlc` tree: `dd2fe9d2168f3fc0963bcdbdac8fa1d487c06e45`
- Phase 1A owner-accepted merge: `c93507c2f2d7e6cec6540ac9a6f155dd6eefecc9`
- Masoretic witnesses: 39
- Chapters: 929
- Verses: 23,213
- Source tokens: 305,507
- Hebrew tokens: 300,679
- Aramaic tokens: 4,828
- Token alignment mismatches: 0

## Rights partitions

The Westminster Leningrad Codex source-script surface is retained as a **Public Domain** layer. OSHB lemma, morphology, source-word ids and language annotations remain a separate **CC BY 4.0** layer attributed to the Open Scriptures Hebrew Bible Project.

No English Scripture text is copied into this package. The 73-book Douay-Rheims corpus remains independent and authoritative for the English Catholic Bible lane.

## Source fidelity

The accepted Phase 1A rules remain unchanged:

- Hebrew and Aramaic Unicode surfaces are preserved verbatim.
- No NFC normalization is applied.
- Canonical tokens are direct verse-child `w` elements only.
- Nested qere/variant words are not duplicated as canonical tokens.
- Lemma and morphology are source annotations, not model-generated data.
- No English gloss is installed.
- No transliteration is installed.

## Douay-Rheims / Masoretic versification gate

The production API does **not** assume that OSHB/WLC and Douay-Rheims verse numbering always match.

For each requested chapter, the runtime compares the numeric verse identity set in the OSHB/WLC source with the installed Douay-Rheims chapter. The Semitic interlinear is served only when those identities match exactly.

If they differ, the API returns `logos_ot_semitic_versification_mapping_required`. It does not renumber, split, merge, shift, or fabricate verses. Those loci require a separately reviewed explicit mapping before production display.

Genesis 1 is the first acceptance locus and is required by CI to have exact OSHB/Douay-Rheims chapter/verse identity before the production package can pass.

## Catholic scope boundary

This package contains the 39 Masoretic/Hebrew-Bible witnesses used within the Catholic Old Testament. It does not duplicate the already accepted Catholic Greek OT package.

- Esther and Daniel here contain their Masoretic portions only.
- Catholic Greek additions to Esther and Daniel remain in `grc_ot_catholic_swete`.
- Tobit, Judith, 1–2 Maccabees, Wisdom, Sirach and Baruch remain in the separate accepted Greek OT production layer.

The two OT original-language production corpora are complementary; neither silently replaces the other.

## API

After deterministic corpus generation on `main` and Cloud Run deployment:

- `GET /api/logos/ot-semitic/catalog`
- `GET /api/logos/ot-semitic/source-rights`
- `GET /api/logos/ot-semitic/interlinear?reference=Genesis%201:1`

The interlinear response exposes source-script surface, lemma, morphology, language and source-word id. It intentionally exposes no gloss or transliteration until separately approved deterministic source/algorithm gates exist.

## Release gate

1. Build Phase 1A from the immutable OSHB source lock.
2. Validate exact accepted counts and token partitions.
3. Package the validated evidence as `heb_arc_oshb_wlc`.
4. Validate Genesis 1 exact DRA/source verse identity.
5. Obtain project-owner acceptance at the exact PR head.
6. Squash-merge.
7. Let the corpus workflow generate and commit the production package on `main`.
8. Deploy the current Cloud Run backend.
9. Verify live catalog, rights and Genesis 1:1.
10. Only then connect this corpus to the normal public Logos **Interlinear** tab.
