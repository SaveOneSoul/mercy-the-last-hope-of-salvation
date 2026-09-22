# Logos Interlinear Source Notice

This file records attribution text for sources verified by the interlinear foundation. It does not grant rights beyond the upstream licences.

## Existing English corpus

**Douay-Rheims American Edition (1899)**  
Rights status recorded by the existing Logos corpus: public domain.  
The installed corpus remains governed by its own generated manifest at `cloud-backend/app/logos_corpus/eng_douay_rheims_1899/manifest.json`.

## Open Scriptures Hebrew Bible

Pinned upstream commit: `3d15126fb1ef74867fc1434be1942e837932691f`

The Open Scriptures licence states that the work is based on the Westminster Leningrad Codex, which is public domain, and licenses the Open Scriptures work under **CC BY 4.0**.

Required attribution recorded from the pinned upstream licence:

> Original work of the Open Scriptures Hebrew Bible available at https://github.com/openscriptures/morphhb

## SBL Greek New Testament

Pinned upstream commit: `c4d241a9c1c479a55b989ba35a4976c1d0b8052c`  
Version recorded upstream: `v1.2`  
Licence: **CC BY 4.0**

Attribution record:

SBL Greek New Testament. Copyright 2010 Society of Biblical Literature and Logos Bible Software. Licensed under CC BY 4.0.

## STEPBible Data

Pinned upstream commit: `ae39711d7843b2902d54993e432de9c12d6a4b9a`  
Licence: **CC BY 4.0**

Attribution required by the upstream README:

**STEP Bible — https://www.STEPBible.org**

Only the published datasets explicitly listed in `sources-manifest.json` are approved at this gate. TAGOT is excluded because the pinned upstream README still lists it among datasets being finished/checked.

## OpenGreekAndLatin First1KGreek

Pinned repository commit: `8ee111eb44ecef4120c844e10749178d95d1f30c`  
Repository licence: **CC BY-SA 4.0**

This source is **not yet approved for bulk Septuagint import**. The exact Swete work/file inventory and per-file provenance still have to be pinned. Any future derived LXX corpus must preserve ShareAlike obligations and remain separable from source layers under incompatible terms.

## Pending sources

The following are deliberately blocked from bulk import by `sources-manifest.json`:

- Clementine Vulgate — exact reusable digital transcription and checksum not yet pinned.
- World English Bible Catholic Edition — optional lane; independent repository-level provenance pin not yet recorded here.

Do not bypass these gates by copying text from an arbitrary website.


## lxx-morph / Rahlfs Greek OT morphology — Phase 2 candidate

Candidate pinned revision: `c91f6b1e8fb3ba37df701e6ae31f675ace71a2b2`

The Phase 2 linguistic source gate records **lxx-morph** as a CC BY 4.0 word-level morphology dataset for the public-domain Rahlfs Septuagint (1935). It is not the same textual edition as the installed Swete/First1KGreek surface witness and must never be presented as if its lemma/POS/morphology were native Swete annotations.

Production import is deliberately disabled until the pinned revision's exact file inventory, license evidence and checksums are verified and deterministic verse/token alignment is demonstrated. Where Rahlfs and the installed Greek surface differ, Logos must preserve separate witness identity or an explicit linguistic gap rather than synthesizing tokens or annotations.

The dataset itself carries a documented quality caveat: it is useful open linguistic data but should not be treated as infallible scholarly authority. Provenance/confidence metadata must remain available when the corpus is eventually integrated.
