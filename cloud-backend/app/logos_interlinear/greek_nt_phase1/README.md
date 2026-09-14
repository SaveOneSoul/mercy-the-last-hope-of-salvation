# Greek NT Expansion Phase 1

This milestone begins only after explicit project-owner acceptance of the deployed John 1:1 interlinear prototype from PR #6.

## Scope

Phase 1 adds a deterministic, validation-only importer for all **27 New Testament books**. It does **not** enable a production Greek corpus yet.

The importer uses two independently pinned source layers:

- **SBLGNT** (`Faithlife/SBLGNT`) for Greek surface text — CC BY 4.0.
- **MorphGNT SBLGNT** (`morphgnt/sblgnt`) for normalized forms, lemmas, POS codes and morphology — CC BY-SA 3.0.

Every source file is pinned by repository commit **and** Git blob SHA-1. The importer recalculates the Git blob SHA-1 from downloaded bytes before parsing.

## ShareAlike boundary

Generated validation data is intentionally partitioned:

- `surface/` contains SBLGNT text tokens and project-derived mechanical transliteration.
- `linguistics/` contains MorphGNT-derived lemma, normalized form, POS and morphology and retains the **CC BY-SA 3.0** obligation.
- `alignment/` contains only project-generated token IDs and exact-alignment metadata. It does not copy Scripture text or MorphGNT linguistic payloads.

Phase 1 does not flatten these source layers into one relicensed corpus.

## No invented glosses

The 27-book importer does **not** manufacture English word glosses. A future gloss layer requires its own approved source, immutable pin, attribution and rights record. The generated manifest explicitly reports that the gloss layer is not installed.

## Deterministic build

Run:

```bash
python scripts/vendor_greek_nt_phase1.py --output build/logos-greek-nt-phase1
python tools/validate_logos_greek_nt_phase1.py --generated build/logos-greek-nt-phase1
```

The build fails if:

- a source file no longer matches its locked Git blob SHA-1;
- the 27-book source inventory changes;
- an SBLGNT verse is missing from MorphGNT or vice versa;
- any word surface differs between the two pinned datasets;
- token positions are not exactly alignable;
- the ShareAlike partition is disabled;
- the output is marked production-enabled.

## Production gate

Successful Phase 1 generation is evidence that the full 27-book corpus can be reproduced and aligned. It is **not** authorization to serve that generated corpus from the production Logos API.

Production integration remains a later gate requiring review of the generated manifest, full-corpus counts, licence partitions, API/storage design, and explicit project-owner approval.
