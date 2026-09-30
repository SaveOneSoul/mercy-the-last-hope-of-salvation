# Mercy Humanoid AI Avatar

The avatar is a public presentation layer over the existing Mercy API. It is not
an autonomous authority and it must not be given repository, admin, database or
deployment privileges.

## Release-1 architecture

- **UI:** static GitHub Pages page at `pages/avatar.html`.
- **Input:** text, touch controls and browser SpeechRecognition when supported.
- **Output:** text plus browser speechSynthesis when supported.
- **Backend:** `/api/avatar/chat` and `/api/avatar/status` in Cloud Run.
- **Doctrine:** explicit Catholic/theological questions route to the existing
  Magisterium AI gateway.
- **Reasoning:** optional Gemini or private Ollama adapter for philosophy, logic,
  science and other in-mission reasoning.
- **Counselling:** local crisis screening runs before any model call. The dedicated
  counselling feature remains the preferred route for personal support.
- **Privacy:** no application transcript storage is added by this feature.
- **Security:** the public avatar refuses source code, credentials, hidden prompts,
  infrastructure details, exploit/bypass help and other private technical data.

## Provider hierarchy

1. Mercy mission and privacy guardrails.
2. Safety/crisis routing.
3. Domain classification.
4. Magisterium AI for Catholic theology/doctrine.
5. Optional Gemini or Ollama for non-doctrinal reasoning.
6. Human follow-up when appropriate.

A secondary reasoning model may explain philosophy, logic or science, but may not
override the Magisterium gateway on Catholic doctrine.

## Production configuration

Set only server-side secrets:

- `MAGISTERIUM_API_KEY`
- `AVATAR_REASONING_PROVIDER=gemini` and `GEMINI_API_KEY`, or
- `AVATAR_REASONING_PROVIDER=ollama` plus a private `OLLAMA_BASE_URL` and model.

Do not expose Ollama directly to the browser. Prefer a private service boundary,
authentication and network restrictions.

## Later specialist agents

CyberSecGPT and `kurbah_ai_sovereign_brain` should be integrated only through
reviewed server-side adapters. For the public Mercy Avatar they should be
capability-limited to safe mission support. They must not expose code-generation,
security exploitation, repository administration, secrets, deployment controls or
private system internals.

## Recommended next milestones

- Reviewed multi-agent consensus object with provenance and disagreement handling.
- Source-grounded philosophy/science corpus for citations.
- Server-side STT/TTS for browsers without suitable Web Speech support.
- Optional 3D/WebGL avatar with lip-sync and accessible reduced-motion mode.
- Khasi speech recognition/TTS evaluation rather than falsely claiming native
  support where browser voices are unavailable.
- Red-team tests for prompt injection, doctrinal bypass, counselling dependence,
  secret extraction and code-generation requests.


## Phase 2 — WebGL humanoid and voice animation

Implemented on the same feature branch:

- dependency-free WebGL humanoid bust renderer with lighting and depth;
- explicit idle, listening, thinking and speaking animation states;
- natural idle head motion and blinking;
- speech-boundary-driven mouth/viseme activity;
- `prefers-reduced-motion` support;
- automatic CSS avatar fallback when WebGL is unavailable;
- stable `window.MercyAvatar3D` adapter so a reviewed GLB/VRM model can replace
  the procedural bust without coupling the model to chat or safety code.

### Lip-sync limitation

Browser `SpeechSynthesisUtterance` does not provide portable phoneme/viseme timing
across all engines. Phase 2 therefore uses word/speech boundary events to animate
the mouth. True phoneme-level lip synchronization should be added only when the
server TTS provider returns timing metadata (phonemes/visemes or word timestamps).

### Photorealistic model gate

Do not add an arbitrary third-party human model by URL. A later GLB/VRM asset must
have documented redistribution/commercial rights, an acceptable polygon/texture
budget, facial blend shapes, mobile performance validation, and a neutral digital
identity that does not impersonate clergy, saints, Jesus, Mary or a real person.
