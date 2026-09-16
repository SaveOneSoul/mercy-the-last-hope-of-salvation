# Logos Greek NT Production Integration

This milestone promotes the owner-accepted **Greek NT Expansion Phase 1** into a production-serving package without changing the existing 73-book Douay-Rheims English corpus.

## Source boundary

The production package preserves the Phase 1 source locks and does not fetch unpinned Scripture or linguistic data at request time.

- **SBLGNT** remains the Greek surface-text layer under **CC BY 4.0**.
- **MorphGNT** remains the lemma/POS/morphology layer under **CC BY-SA 3.0**.
- Project-generated alignment metadata contains token ids and integrity metadata only.
- The two source-derived layers are stored in separate directories and remain separately attributed in API responses.
- No English gloss layer is installed because no separately approved gloss source has been accepted yet.

## Production package

Default path:

`cloud-backend/app/logos_corpus/grc_sblgnt_morphgnt/`

Layout:

```text
grc_sblgnt_morphgnt/
  manifest.json
  phase1/
    manifest.json
    surface/
      MAT.json ... REV.json
    linguistics/
      MAT.json ... REV.json
    alignment/
      MAT.json ... REV.json
```

The embedded `phase1/` directory is copied verbatim from a newly generated and revalidated Phase 1 build. The top-level `manifest.json` is the production-serving contract.

## Validated corpus contract

The promotion gate is locked to the accepted Phase 1 evidence:

- 27 New Testament books;
- 260 chapters;
- 7,939 SBLGNT verses;
- 137,741 SBLGNT surface tokens;
- 7,927 verses with MorphGNT annotations;
- 12 explicit source-locked MorphGNT annotation gaps at John 7:53–8:11;
- zero unresolved lexical mismatches.

John 7:53–8:11 is never silently filled. The SBLGNT surface text remains available, while the linguistic partition reports `unavailable-in-pinned-morphgnt` and contains no fabricated morphology.

## API

The existing English Logos routes are unchanged. Greek production data is exposed through a separate namespace:

- `GET /api/logos/greek/catalog`
- `GET /api/logos/greek/source-rights`
- `GET /api/logos/greek/interlinear?reference=John%201:1`

The interlinear response preserves three logical partitions: `surface`, `linguistics`, and `alignment`. A compatibility `tokens` view is also returned for UI rendering, but the source and license metadata remain explicit in the same response.

Old Testament references sent to the Greek NT endpoint return `logos_greek_nt_reference_required` rather than attempting to substitute Septuagint material. Septuagint/deuterocanonical Greek remains a separate future source-lock milestone.

## CI and promotion

Pull requests build the production package in a temporary directory and validate it without committing generated corpus data.

After owner acceptance and merge to `main`, the Logos corpus workflow:

1. rebuilds and validates Phase 1 from the pinned SBLGNT/MorphGNT sources;
2. promotes the validated output to the production package path;
3. validates production counts, licenses, partitions and the John 7:53–8:11 gap policy;
4. regenerates the existing 73-book Douay-Rheims corpus independently;
5. commits deterministic corpus changes only when generated data differs.

This preserves the existing English corpus while adding a separately auditable Greek NT production lane.
