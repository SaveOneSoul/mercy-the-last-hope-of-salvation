# Mercy Voice Khasi Corpus Specification v0.1

Status: design and collection gate; no Khasi TTS support is claimed.

## Recording target

Use recordings only from speakers who explicitly consent to TTS training,
evaluation, derivative model creation, and the intended distribution/use of the
resulting voice. Keep consent/provenance metadata separate from public text.

Preferred capture: mono PCM WAV, 48 kHz, 24-bit master; quiet untreated room;
consistent microphone position; no music, reverb, denoising, compression, or
voice effects. Training exports may be resampled later without replacing masters.

## Required corpus strata

1. Khasi phonetic coverage: vowels, consonant clusters, glottal/aspirated
   contrasts, common function words, numbers, dates, punctuation and questions.
2. Normal conversation: greetings, directions, family/community life, school,
   work, weather and natural dialogue at varied sentence lengths.
3. Catholic vocabulary: Eucharist, Trinity, Sacraments, Magisterium, mercy,
   repentance, grace, salvation, Holy Spirit, Church, parish and liturgy.
4. Scripture/proper names: Jesus Christ, Mary, Joseph, Peter, Paul, Isaiah,
   Jeremiah, Abraham, Moses, Jerusalem, Bethlehem, Nazareth and book names.
5. Prayer/devotional register: short prayers, intercessions, Scripture-style
   prose and reverent longer passages without copying restricted translations.
6. Evaluation-only holdout: unseen sentences covering all strata; never train on
   this partition.

## Manifest

Each clip receives a stable ID and fields:
`audio_path, transcript, language, speaker_id, consent_id, category,
recorded_at, sample_rate, bit_depth, duration_seconds, split`.

Do not place legal names, contact details, signatures or consent documents in the
public repository. The public manifest uses pseudonymous IDs.

## Acceptance gate

Khasi support remains disabled until human Khasi reviewers evaluate the holdout
set for intelligibility, pronunciation, Catholic terminology/proper names,
naturalness, reverent-register suitability and harmful meaning changes.
Record scores and error categories; do not promote solely on an aggregate metric.
