# Mercy Voice Service

Private TTS boundary for the Mercy Humanoid Avatar.

## Contract

- `GET /health`
- `POST /v1/synthesize`
- input: text, language (`en` or `kha`), voice, return_timing
- output: base64 audio, MIME type, optional timing metadata

The default engine is `contract_only`. It does **not** claim to synthesize speech.
Contract-test audio is disabled unless `MERCY_VOICE_ENABLE_CONTRACT_AUDIO=true`.

No open-source neural TTS engine is committed here until its current model/code
license, redistribution/commercial terms, deployment requirements, and language
coverage are reviewed. Khasi remains `corpus_evaluation_required`; support must
be demonstrated with the dedicated Khasi corpus rather than inferred from a
"multilingual" label.

## Security

Deploy as a separate private service. Prefer Cloud Run IAM/OIDC for production.
The bearer-token mode exists as an interim staging boundary. Never expose the
service token to browser JavaScript. No transcript persistence is implemented.

## Environment

- `MERCY_VOICE_ENGINE=contract_only`
- `MERCY_VOICE_SERVICE_TOKEN=`
- `MERCY_VOICE_ALLOW_UNAUTHENTICATED=false`
- `MERCY_VOICE_ENABLE_CONTRACT_AUDIO=false`


## Reviewed English engine

The first English candidate is Kokoro-82M. Upstream model metadata identifies the
weights as Apache-2.0 and the current inference library is Apache-2.0. The runtime
uses espeak-ng through the phonemization stack; keep the voice service as a
separate deployable component and retain the applicable notices/source-offer
obligations for distributed images.

Set:
- `MERCY_VOICE_ENGINE=kokoro`
- `MERCY_KOKORO_VOICE=af_heart`

Kokoro is used for English only. Requests with `language=kha` fail closed until
a Khasi model has passed the dedicated corpus/pronunciation gate.
