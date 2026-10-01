# Mercy 3D avatar asset gate

The Mercy Avatar renderer supports a local reviewed VRM/GLB character, but no third-party character asset is committed by this change.

## Acceptance requirements

Before setting `data-model-url` on the avatar viewport and committing an asset:

- Record the exact asset name, version or immutable source identifier, creator/publisher, source URL, retrieval date, and cryptographic checksum.
- Preserve the complete license/terms that apply to that exact asset.
- Confirm that website use, modification, and repository redistribution are permitted.
- Record attribution requirements and prohibited uses.
- Confirm the model is a fictional adult character and is suitable for the Mercy mission presentation.
- Verify required facial expression/blendshape support for speech and state animation.
- Review the asset for unexpected scripts, external network dependencies, excessive size, and unsafe/unneeded extensions.
- Keep the asset local to the site after approval; do not silently load arbitrary remote character URLs.

Until this gate is completed, the page intentionally shows a neutral “3D avatar not installed” state. The old hand-built SVG face is not a fallback.

The renderer preserves the existing `window.MercyAvatar3D.setState`, `setViseme`, and `pulseSpeech` interface so microphone, conversation, staging API, and voice integration can remain unchanged.
