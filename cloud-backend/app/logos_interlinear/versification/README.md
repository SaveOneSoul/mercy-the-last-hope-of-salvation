# Logos Versification Mapping Registry

This directory stores **reference mappings only**. It never rewrites Scripture source text.

The canonical reference system is the vendored **Douay-Rheims American Edition (1899)** Catholic 73-book corpus. Hebrew/Aramaic, Greek, and Latin witnesses retain their own immutable chapter/verse boundaries and surfaces.

A source lane may be rendered verse-for-verse against Douay-Rheims only when either:

1. the audited chapter/verse identifiers are exactly identical; or
2. an explicit mapping file is registered here with `status: verified` and passes the repository validator.

Until then, runtime must expose the lane as `mapping-required` rather than manufacture an alignment.

## Registry

`index.json` is the only registry entry point. Each row in `mappings` has this shape:

```json
{
  "book_id": "JDT",
  "lane": "latin",
  "status": "verified",
  "file": "maps/jdt-latin.json"
}
```

Allowed lanes are `semitic`, `greek`, and `latin`.

## Mapping file contract

Each mapping file is versioned and source-specific:

```json
{
  "schema_version": 1,
  "mapping_version": "2026.09.17-jdt-latin-v1",
  "book_id": "JDT",
  "lane": "latin",
  "status": "verified",
  "canonical_reference_system": "douay-rheims-1899",
  "source": {
    "source_id": "vulgate-clementine",
    "reference_system": "clementine-vulgate"
  },
  "policy": {
    "source_text_immutable": true,
    "fabricated_boundaries_forbidden": true,
    "bidirectional_validation_required": true
  },
  "coverage": {
    "complete_for_audited_mismatches": true,
    "audited_mismatch_chapters": ["16"]
  },
  "chapters": [
    {
      "canonical_chapter": "16",
      "segments": [
        {
          "id": "jdt-lat-16-a",
          "relationship": "renumber",
          "canonical_refs": [{"chapter": "16", "verse": "1"}],
          "source_refs": [{"chapter": "16", "verse": "1"}],
          "evidence": {
            "citation": "Pinned-source comparison and documented versification evidence",
            "note": "Explain why this relationship is verified."
          }
        }
      ]
    }
  ]
}
```

The example above is illustrative only; it is **not** a verified Judith mapping.

Allowed relationship values are `identity`, `renumber`, `offset`, `split`, `merge`, `range`, `component-range`, `source-only`, and `canonical-only`.

For `component-range`, an opaque `source_locus` may be used when forcing artificial verse boundaries would corrupt the source witness. For ordinary mappings, `canonical_refs` and `source_refs` must enumerate real source/canonical references.

A `verified` file must provide evidence for every segment, must cover exactly the audited mismatch chapters it claims to resolve, and must pass bidirectional duplicate/coverage checks. Draft mappings may be stored but never change runtime alignment status.

If a pinned source and Douay-Rheims have the same numeric verse identifiers but comparison proves that the content boundaries are shifted, the file may additionally declare `coverage.verified_override_chapters`. Such chapters require `complete_for_numeric_identity_overrides: true` plus a chapter-keyed `numeric_identity_override_evidence` citation. A verified override takes precedence over apparent numeric identity at runtime; equal verse counts alone are never sufficient evidence of alignment.

If the source tradition contains a chapter that has no same-numbered Douay chapter because its verses are fully mapped into another canonical chapter, declare that source chapter in `coverage.structural_source_chapters`. A verified mapping must also set `complete_for_structural_source_chapters: true`, provide `structural_source_chapter_evidence`, and prove that every verse of that pinned source chapter is consumed by the enumerated cross-chapter mappings. This records chapter-structure differences without creating or deleting Scripture divisions.

## Integrity rules

- Never edit or renumber the imported source corpora to make them match Douay-Rheims.
- Never synthesize Greek, Hebrew/Aramaic, or Latin verse boundaries.
- Never infer a one-to-one mapping from equal verse counts alone.
- Preserve `split`, `merge`, and `component-range` relationships explicitly.
- A verified mapping must be reproducible from pinned sources and evidence.
- Existing Esther, Daniel, and Baruch component mappings remain authoritative until deliberately migrated into this registry with equivalent or stronger evidence.
