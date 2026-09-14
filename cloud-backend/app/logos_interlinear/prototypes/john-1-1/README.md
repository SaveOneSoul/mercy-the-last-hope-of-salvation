# John 1:1 Interlinear v1 Prototype

This directory is the first executable gate after the Logos interlinear corpus foundation.

It is intentionally limited to **John 1:1**. It verifies that one verse can be represented with field-level provenance, source-locked Greek text, lemma and morphology, project-derived transliteration, project-authored study glosses, deterministic JSON, and semantic HTML/CSS rendering before any 27-book New Testament expansion is allowed.

## Source separation

- Greek surface text: pinned Faithlife SBLGNT, CC BY 4.0.
- Lemma, part-of-speech, and morphology: pinned MorphGNT analysis, CC BY-SA 3.0.
- Transliteration: derived by the Mercy/Logos prototype.
- Short glosses: project-authored study aids; they are not an English Bible translation.
- English Scripture remains the installed Douay-Rheims corpus and is not embedded in this prototype artifact.

The MorphGNT annotation layer is ShareAlike. Its rights and attribution are kept explicit rather than being flattened into the licence of another source.

## Gate

Run:

```bash
python tools/validate_logos_interlinear.py
python tools/validate_logos_interlinear_prototype.py
```

The validator requires the exact 17 SBLGNT John 1:1 token surfaces, the exact MorphGNT lemma/morphology rows recorded for the pinned John file, contiguous positions, required canonical token fields, source pins and blob SHAs, and the static renderer/public-data wiring.

**Do not scale to the 27-book Greek New Testament from this directory until this prototype gate passes and the project owner explicitly approves the scaling milestone.**
