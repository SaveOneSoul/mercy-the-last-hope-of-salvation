# OT Greek Production Integration — Acceptance Checklist

This checklist applies to the exact PR head proposed for the Old Testament Greek Production Integration milestone.

Acceptance requires all of the following:

- Phase 1B acceptance merge remains `22ad0019355d6924592d3c6b5176624e6fd4c866`.
- The production package deterministically rebuilds the accepted 15 witnesses and 5,337 source verse records.
- All source Greek remains under the isolated CC BY-SA 4.0 partition.
- The accepted Catholic/Douay mapping file is copied byte-for-byte as JSON data and not reinterpreted into fabricated source boundaries.
- Tobit, Judith, 1–2 Maccabees, Wisdom and Sirach use exact chapter/verse identity mapping.
- Baruch 1–5 uses the Baruch witness and Baruch 6 uses the Epistle of Jeremiah witness.
- Esther remains component-range where exact Greek/Douay verse equivalence is not established.
- Daniel uses Theodotion as the Catholic integration lane while Old Greek remains a separate parallel witness.
- Daniel 14 preserves the 36-source-verse Theodotion Bel witness against the 42-verse Douay-Rheims range without synthesizing six Greek verses.
- No English Scripture text, gloss, lemma, morphology or transliteration is invented in this Greek OT package.
- `/api/logos/ot-greek/catalog`, `/api/logos/ot-greek/source-rights`, and `/api/logos/ot-greek/interlinear` are mounted in the backend.
- Existing Douay-Rheims, OSHB/WLC, and Greek NT production packages remain unchanged.
- Vendor Logos Catholic Bible Corpus, Mercy Backend Smoke, and Public Form Audit must all succeed at the exact head.
- Production corpus generation on `main`, Cloud Run deployment, and live endpoint verification remain post-merge gates. Frontend integration is a later milestone.
