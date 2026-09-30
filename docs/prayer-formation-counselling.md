# Prayer, formation and counselling release

## Public entry points

- Prayer Library → Mary Our Help: five dedicated reading pages, a related link to the existing Precious Blood page, seven Holy Wounds prayers, and two original source PDFs.
- Codex Fidei → Mariology: ten expanded lessons, retaining the existing course ID and progress.
- Codex Fidei → Psychology: ten introductory lessons.
- Counselling → Counselling Foundations and Pastoral Accompaniment: ten lessons each.
- Counselling → AI Counselling Support and Personal Support Companion.

Lessons include original explanations, reading links, fictional exercises and authored questions. Certificates record internal learning only, not clinical qualifications. Assignments are self-directed, not professionally graded. Course drafts are device-local and should contain no real client details.

## Source and permission record

Mary Our Help's 28 September 2026 email permits use and sharing with acknowledgment and a link. The owner retains the email privately. Attribution appears on the collection and every prayer page, with a Sources acknowledgment. `data/prayers/sources.json` records original URLs, retrieval date and SHA-256 values. Original PDFs are byte-for-byte preserved; native text views retain extracted wording and page order. Whitespace/layout differ. The Holy Wounds selection contains seven complete prayers, not the entire source site's collection.

No new Precious Blood America / Adorers edition is transcribed. Its existing page and separate reference remain unchanged. Mary Our Help's permission is not represented as permission for that third-party edition.

## AI activation

The frontend is deployable without a key. It truthfully reports unavailability and provides written exercises and human-help contacts. The cloud backend adds `/api/counselling/status` and `/api/counselling/chat`; the existing Magisterium Catholic AI is unchanged.

Live AI is off by default. It requires a separate server-side OpenAI credential, an explicit model ID supporting the Responses API, and `COUNSELLING_ENABLED=true`. The provider account needs access to `omni-moderation-latest`. Never put credentials in browser configuration, this repository, a chat message or a PR.

From a trusted machine already authenticated to the owner's Google Cloud project, deploy the new backend with the existing PowerShell script:

```powershell
# Ordinary deployment leaves AI support disabled.
./cloud-backend/deploy-gcp.ps1

# Activation prompts securely for the key if its Secret Manager secret is absent.
# Replace the example value with a model approved in your OpenAI project.
./cloud-backend/deploy-gcp.ps1 -EnableCounselling -CounsellingModel "YOUR_MODEL_ID"
```

Use the activation flags again on subsequent deployments to retain the enabled configuration. Without them, the script disables this optional feature. Enabling support sets maximum instances to one because the initial abuse counters are in memory. They reset on restart and are not a durable spending limit. Configure provider-level project budgets and monitoring; add a distributed limiter before scaling the feature. Disabling support restores the existing three-instance limit.

Check `/api/counselling/status` after deployment. Then test an ordinary fictional concern, an urgent-help phrase, and a provider outage before inviting users. No live provider evaluation has been performed in this release without the owner's credential; transport and safety contracts are tested with mocked provider responses. Model behaviour still requires ongoing review.

## Data handling and limits

- Adult consent is required before remote support; optional faith support is off by default.
- Messages are held in page memory, with at most eight recent turns forwarded. No transcript DB, application transcript logs, remote agent tools or stored provider conversation IDs are used. Replies are rendered as text.
- Only an explicitly remembered goal category is saved for the Personal Companion. Clearing aborts an in-flight browser request, clears page memory and removes the saved goal. It cannot retract a request already sent.
- Requests use `store:false`, but that is not a claim of provider zero retention. The page explains provider processing and links its current data policy.
- Local urgent-help routing precedes provider calls; moderation checks input and output. These checks cannot detect all crises and are not clinical assessments. Human-help contacts remain visible independently of AI availability.
- English is the primary supported language. A few additional urgent phrases are recognised, but no comprehensive multilingual safety claim is made.
- API responses are `no-store`; the service worker excludes API paths. Counselling pages do not load analytics, live editing or CMS overrides.

## Validation

```bash
python tools/validate_prayer_formation_care.py
python tools/audit_public_forms.py
python tools/validate_theology_hub.py
python tools/validate_logos_greek_frontend.py
cd cloud-backend
python -m unittest discover -s tests -p test_counselling.py -v
```

The release also received local DOM interaction checks for day 27/28/54, saved progress, course quizzes/completion, assessments, optional goal storage, privacy clearing, text-safe replies, local crisis handling and offline exercises. A real mobile-browser render was not available in the build environment; responsive CSS and semantic controls are included, but this is not equivalent to device testing.

Two pre-existing static validation assumptions were updated: formation navigation may go through Codex Fidei, and the Logos cache version may be v16 or later. No Logos runtime code was changed.
