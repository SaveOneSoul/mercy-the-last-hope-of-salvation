# Mercy Original 3D Character Pipeline

Status: development-only. PR #121 remains draft. No production deployment.

## Decision

Mercy will use an original project-owned character rather than a third-party stock avatar. The production path is Blender -> humanoid rig -> facial shape keys -> VRM 1.0 -> local website asset.

No generated CSS/SVG person is an acceptable fallback. Until the original binary is exported and reviewed, the site must show the neutral 3D placeholder.

## Character brief

- Fictional adult woman; not based on or intended to resemble a real person.
- Modest, dignified, peaceful and approachable presentation.
- Not Mary, a saint, a religious sister, clergy, or an apparition.
- Neutral contemporary modest clothing; no habit, veil, halo, crown, or sacred-person impersonation.
- Warm facial proportions suitable for counselling/pastoral UI without implying human identity.
- Upper-body presentation is the primary web framing; full humanoid rig is retained for future animation.

## Geometry and materials

Build an original base mesh in Blender. Keep topology deformation-friendly around eyelids, lips, jaw, shoulders and elbows. Use project-created textures/materials only. Do not import third-party human meshes, clothing, textures, hair, rigs or generated assets whose redistribution provenance cannot be documented.

Target a web-efficient model. Optimize only after expression and deformation tests pass.

## Humanoid rig

Required VRM humanoid assignments include hips, spine, chest, neck, head, upper/lower arms, hands, upper/lower legs and feet, with left/right assignments as required by VRM 1.0. Add eye bones if the final design uses bone-driven gaze.

## Facial expression contract

The exported model must provide at minimum:

- blink / blinkLeft / blinkRight
- aa
- ih
- ou
- ee
- oh
- happy
- relaxed
- surprised

The web renderer may initially use aa as the compatibility viseme, but the model must retain the broader mouth set so later TTS timing can drive richer lip sync.

## Runtime contract

The existing browser interface remains stable:

- MercyAvatar3D.setState(state)
- MercyAvatar3D.setViseme(value)
- MercyAvatar3D.pulseSpeech()

States: idle, listening, thinking, speaking, error.

No model URL may point to an arbitrary remote character. The approved final VRM is hosted locally under assets/avatar/mercy/.

## Proposed repository output

assets/avatar/mercy/
- mercy.vrm
- SHA256SUMS
- PROVENANCE.md
- LICENSE

The binary is not committed until the Blender export has been visually reviewed and the checksum recorded.

## Validation gate

Before wiring data-model-url:

1. Confirm the character is original and adult-presenting.
2. Confirm no third-party unapproved asset is embedded.
3. Validate humanoid bone assignments.
4. Validate required expression names and deformation quality.
5. Test blinking, gaze and mouth shapes.
6. Test neutral/listening/thinking/speaking state transitions.
7. Test desktop and mobile framing.
8. Measure VRM file size and browser load time.
9. Record SHA-256.
10. Commit provenance and ownership notes with the exact binary.
11. Keep PR #121 draft until CI, browser, voice, safety and asset review gates pass.

## Tooling

Use Blender plus the VRM Add-on for Blender. Prefer VRM 1.0. Keep the editable .blend source outside the public runtime path unless the project explicitly chooses to version it later.

## Production boundary

This document does not authorize production deployment or merge. Production remains untouched until separate project-owner approval.
