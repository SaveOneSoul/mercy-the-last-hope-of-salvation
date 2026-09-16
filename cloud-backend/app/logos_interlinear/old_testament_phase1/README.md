# Logos Old Testament Expansion — Phase 1A

Phase 1A adds a deterministic, validation-only Hebrew/Aramaic corpus build for the 39 Masoretic/Hebrew-Bible witnesses that overlap the Catholic Old Testament.

It does **not** claim to complete the Catholic 46-book Old Testament original-language layer. The Catholic deuterocanonical books and the Greek additions to Esther and Daniel require a separately validated Septuagint/deuterocanonical source inventory.

## Locked source

- Open Scriptures Hebrew Bible / Westminster Leningrad Codex
- Repository: `openscriptures/morphhb`
- Commit: `3d15126fb1ef74867fc1434be1942e837932691f`
- Locked `wlc` tree: `dd2fe9d2168f3fc0963bcdbdac8fa1d487c06e45`
- WLC text: public domain
- OSHB lemma and morphology: CC BY 4.0

The importer verifies the immutable `wlc` tree inventory and each downloaded source file against the Git blob SHA-1 returned by that locked tree, then records SHA-256 integrity metadata in the generated manifest.

## Data contract

For each direct `<w>` child of an OSIS `<verse>`, Phase 1A preserves:

- exact source surface text
- source word ID
- lemma
- morphology code
- token-level language (`he` for morphology prefix `H`, `arc` for prefix `A`)
- optional upstream word metadata such as `type` and `n`

Nested qere/variant `<w>` elements inside notes are not duplicated as canonical verse tokens. The source XML remains authoritative for those variants.

The OSHB source explicitly warns against NFC normalization of Hebrew. Accordingly, generated source surfaces are copied verbatim and the importer performs no Unicode normalization.

## Deliberate omissions

Phase 1A does not add English word glosses, transliteration, or automatic Masoretic-to-Douay-Rheims verse remapping. Those are separate gates and must not be invented or inferred silently.

The build output is temporary CI evidence under `build/logos-old-testament-phase1` by default. It is not committed as a production corpus and `production_enabled` remains `false`.

## Catholic completeness boundary

The Hebrew/Aramaic build covers 39 source books. Esther and Daniel are only the Masoretic portions relative to the Catholic canonical form. The following Catholic material remains outside Phase 1A: Tobit, Judith, Greek additions to Esther, 1 Maccabees, 2 Maccabees, Wisdom, Sirach, Baruch, and Greek additions to Daniel.

`lxx-inventory-gate.json` records the separately pinned First1KGreek/Swete candidate and keeps it blocked until exact Catholic work/file mapping, per-file provenance, versification mapping and ShareAlike isolation are validated.
