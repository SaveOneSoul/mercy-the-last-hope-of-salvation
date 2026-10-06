# Shared AI Core & AI Ministry — foundation v1

Mercy owns all **Catholic** doctrine, Scripture, pastoral, church teaching, ministry tools and associated private drafts. Insurance business logic and policy information must never be imported into Mercy.

## Architecture and deployment
- `cloud-backend/app/shared_ai_core.py` implements a domain-neutral provider/authorization/validation/audit contract, version 1.0. Insurance implements the matching contract in JavaScript.
- The two deployments share **interfaces**, not database tables, credentials, secrets, user identities or runtime service accounts. Move this contract into independently versioned reusable packages after CI compatibility tests are established.
- Route/controller code must use services and provider adapters and must not invoke external LLMs directly.
- Domain-specific doctrinal validation must distinguish Magisterium from theological opinion, private revelation, paraphrases and AI-generated synthesis. Sources must be verified before citation.
- `ai_ministry_policy.py` defines a fail-closed permission and private-menu policy. It does not expose any public ministry endpoint or page. Only independently verified server-side signed sessions can yield roles/permissions.
- Owner authority comes from an authenticated, securely provisioned owner account, never a hard-coded email/phone bypass.
- Ministry access levels include priest, deacon, seminarian, religious, catechist, youth leader and editor, with least-privilege capabilities; these titles alone do not confer `ministry:publish`.
- Homily generation is **request-driven only**. No scheduled generation, unsolicited reminders or automatic publishing.
- Drafts remain private until authorized review and explicit publish; separate Firestore collections may later include `homily_drafts`, `published_homilies`, `retreats`, `catechesis`, `lesson_plans`, `templates`. Enforce server-side owner/tenant document access and audit writes.
- This is a contract/security foundation only. No live ministry UI, storage integration, provider wiring or deployment is asserted.
- Before production activation: wire verified session principals into service guards; add persistence, scoped queries, CSRF and rate limits; add tests for direct endpoint attacks, external provider citation fabrication, publishing, and audit privacy.
