# Logos Old Testament Expansion — Phase 1B

Phase 1B builds **validation evidence only** for the Greek deuterocanonical material and the Greek additions to Esther and Daniel required by the Catholic 46-book Old Testament. It does not enable production serving.

## Source and rights boundary

The phase is locked to `OpenGreekAndLatin/First1KGreek` commit `8ee111eb44ecef4120c844e10749178d95d1f30c` and the immutable Septuaginta tree `e1fe137e1409d0a73a52ddac6ba9669fcbc3ba79`.

Selected Swete TEI editions are licensed **CC BY-SA 4.0**. Generated Greek data therefore stays physically isolated under:

`sharealike/first1kgreek_swete_cc-by-sa-4.0/`

Nothing from this phase is flattened into the public-domain Douay-Rheims corpus, the OSHB/WLC partitions, or the Greek New Testament package.

## Catholic scope

The source lock covers Tobit, Judith, 1–2 Maccabees, Wisdom, Sirach, Baruch, the Epistle of Jeremiah as Catholic Baruch 6, integrated Greek Esther, and the Greek Daniel witnesses.

For Daniel, both **Old Greek** and **Theodotion** witnesses are preserved. Theodotion is the Phase 1B Catholic/Douay-Rheims integration lane for Daniel 3:24–90, Susanna (Daniel 13), and Bel and the Dragon (Daniel 14). Old Greek remains a separate parallel witness and is never silently collapsed into Theodotion.

Sirach deliberately selects `tlg0527.tlg034.1st1K-grc2`, the Swete edition. The separate `grc1` Codex 248/Hart edition is not used as the Phase 1B Swete witness.

## Versification contract

`versification-map.json` is mapping metadata, not a text-rewriting instruction.

Simple deuterocanonical books use verified identity chapter/verse mapping. The Epistle of Jeremiah maps to Catholic Baruch 6. Esther uses component-range mappings because the integrated Greek source and Douay-Rheims/Vulgate presentation do not always permit a safe one-to-one verse split; in particular, the B8–9 material spans Douay-Rheims Esther 15:1–3 and must not be artificially divided.

The importer preserves source loci and source Greek surfaces. It does not invent English glosses, lemmas, morphology, transliteration, or synthetic verse divisions.

## Validation-only promotion gate

Phase 1B remains:

- `production_enabled: false`
- `production_import_allowed: false`
- owner acceptance required

CI must verify every selected metadata/text Git blob, the per-file CC BY-SA 4.0 declaration, deterministic TEI extraction, ShareAlike isolation, the Catholic mapping contract, and source sanity checks. A later production-integration phase may enable serving only after exact-head owner acceptance.
