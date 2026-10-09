# Divine Mercy WhatsApp and Homily Service

Status: implementation specification; the new WhatsApp channel is not activated by this document.
Requested: 9 October 2026.
Project: Save One Soul — Mercy, The Last Hope of Salvation.

## Decision and purpose

Implement the existing Homily Service through the proposed Divine Mercy WhatsApp channel, reusing Mercy's Catholic ministry backend. The channel will welcome visitors in the Name of Jesus, help them find existing Save One Soul services, and keep their messages available to Rivaldo.

The requested account is currently an ordinary WhatsApp account. The intended setup is the WhatsApp Business app plus the official WhatsApp Business Platform, using coexistence if the account is eligible. Coexistence eligibility and the provider must be confirmed before activation. Creating this file does not migrate the number, purchase a plan, send messages, or deploy a chatbot.

## Requirements agreed for this channel

- Keep the existing phone number as the intended ministry contact.
- Send an automatic welcome and services menu when someone first contacts the ministry.
- Welcome that person again only when they send a new message after **seven consecutive days without conversation**.
- People who chat daily, on alternate days, or at any interval shorter than seven days must not receive another automatic welcome.
- Deliver incoming messages to Rivaldo's inbox and provide an owner notification independently of whether a greeting is due.
- Allow Rivaldo to take over a conversation and pause its automated replies.
- Integrate the existing request-driven Homily, Preaching and Seminar work.
- Preserve Catholic doctrinal grounding, private drafting, and explicit review before publication.

## Existing work to reuse

Source inspected at Mercy commit `bc2761e2b5c11aab559528a8720f8dc2a50cd3d7`. This records source capabilities, not a claim that every route is deployed or operational.

| Existing component | Role in this integration |
| --- | --- |
| [Homiletics library](../pages/homiletics.html) | Public homilies, sermons, exhortations, retreat talks and pastoral preaching. Homiletics stays distinct from formal Codex courses. |
| [AI Ministry service](../cloud-backend/app/ai_ministry.py) | Request-driven generation; private draft storage through the admin API; edit, review and publish transitions. |
| [Private ministry bridge](../cloud-backend/app/ministry_bridge.py) | Signed server-to-server access to the same generation pipeline. |
| [Ministry access policy](../cloud-backend/app/ai_ministry_policy.py) | Authenticated identity, domain and permission checks for private ministry functions. |
| [Shared ministry contract](SHARED_AI_CORE_MINISTRY_V1.md) | Domain separation, Catholic-source grounding and private ministry principles. |

The existing owner-only WhatsApp adapter already recognizes `HOMILY`, `PREACHING` / `PREACH` / `PROCLAMATION`, and `SEMINAR`. Reuse its interaction contract through a ministry-specific adapter; keep unrelated business data, identities and credentials separate.

The old scheduled homily delivery workflow has been removed. Its historical reminder documentation must not be used to restore scheduled generation. Separate Divine Mercy prayer reminders are outside this change.

### Preserve these ministry behaviours

- **Homily:** use the supplied liturgical date and context, correct Sunday cycle or weekday readings, season, solemnity or feast. Ask for the date/readings when they cannot be verified. Do not invent a reading set.
- **Preaching / proclamation:** require a Scripture passage; ask for it when missing.
- **Seminar:** require a topic/theme and prepare structured Catholic teaching.
- **Generation pipeline:** Magisterium grounding, optional Gemini refinement, and Magisterium verification of a refined response. Retain the existing grounded fallback when final verification fails; an unverified refinement must not be presented as verified.
- Distinguish doctrine, discipline, theological opinion, devotional practice and private revelation. Preserve verified sources and do not invent citations.
- Generate only after an authorized request. Keep generated material private until review and explicit publication.

## Public menu and private ministry access

The visitor menu offers existing public resources. Selecting Homily Service does not grant access to private draft generation.

| Visitor option | Destination or action |
| --- | --- |
| Homily Service | Open [Homiletics](../pages/homiletics.html), or ask Rivaldo for help. Serve only material approved for public access. |
| Divine Mercy and prayer | [Divine Mercy](../pages/divine-mercy.html), [Chaplet](../pages/divine-mercy-chaplet.html) and [Devotions](../pages/devotions.html). |
| Scripture — Logos | [Logos Bible study](../pages/logos.html). |
| Catholic formation | [Codex Fidei](../pages/codex-fidei.html). |
| Saints and Church Fathers | [Saints](../pages/saints.html) and [Church Fathers](../pages/fathers.html). |
| Speak with Rivaldo | Put the conversation into human-handoff mode and notify Rivaldo. |

Use an allowlisted mapping of menu IDs to these site routes. Render a normal WhatsApp reply with a supported list or buttons; do not promise a forced device popup. Keep the menu available on demand through `MENU`, without treating that as a fresh automatic welcome.

Suggested welcome copy:

> Greetings in the Name of Jesus Christ! Welcome to Save One Soul — Divine Mercy Service. I am the automated welcome assistant. Choose Homily Service, Divine Mercy and prayer, Scripture — Logos, Catholic formation, Saints and Church Fathers, or Speak with Rivaldo. You may also leave your message here for Rivaldo. Jesus, I trust in You!

The notification path must be functioning before this greeting is enabled.

### Private Homily Service

Only a verified ministry identity may request generation or access private drafts. A contact's display name, a typed phone number, a public menu selection or a claim such as “I am the owner” is not authentication.

The current bridge authenticates its calling service and uses a fixed owner context. It is not a public or multi-user authorization system. Keep it behind the verified owner route; extending it to other ministry users requires explicit identity binding and permission checks.

Because the requested sender number is also Rivaldo's current personal number, do not assume the owner can operate the bot by sending WhatsApp API messages to that same number. Keep the existing authenticated Mercy ministry dashboard as the owner entry point unless a supported, verified owner-command channel is configured. App-sent message echoes represent manual conversation activity, not authorization to run ministry commands.

The current admin generation route saves a draft, while the bridge returns generated text and sources without saving a draft. Integration work must connect WhatsApp-requested generation to authorized private persistence before claiming a saved draft or offering review/publication. Do not expose a draft through a public URL.

## Seven-day greeting rule

Apply the rule to each one-to-one conversation independently, scoped by the ministry account and the contact's stable platform identifier. Seven days means **168 elapsed hours**, using server-side UTC timestamps. Display dates in Asia/Kolkata where needed.

Before updating the stored timestamp for an incoming message:

1. Verify the webhook and deduplicate the platform message ID.
2. Read the previous human conversation activity.
3. Make the greeting decision and record the new activity atomically.
4. Queue any required greeting and owner notification with separate delivery tracking.
5. Continue menu routing or human handoff as appropriate.

Count received human messages and Rivaldo's sent replies as conversation activity, including supported Business-app echoes. Automated greetings, delivery/read receipts, webhook retries and unrelated reminder jobs must not restart the inactivity timer.

| Event | Expected behaviour |
| --- | --- |
| Confirmed first contact | Send one welcome/menu and notify Rivaldo. |
| Incoming message after less than 168 hours | No repeated automatic welcome; notify Rivaldo. |
| Incoming message at or after 168 hours | Send one welcome/menu and notify Rivaldo. |
| Alternate-day messages over several weeks | No repeated automatic welcome. |
| Seven days elapse with no new message | Send nothing; wait for the person to return. |
| Rivaldo replies during the gap | Restart the inactivity measurement from that reply. |
| Duplicate webhook or simultaneous incoming messages | Process each unique message once; queue at most one welcome for that return. |
| Human handoff is active | Keep automation paused and notify Rivaldo; handoff takes priority over a due greeting. |

Use supported history synchronization or seed known conversations before enabling the rule. When prior activity is unknown, do not describe an existing contact as first-ever: use an activation baseline for that known contact until reliable activity is available.

Persist conversation activity, handoff state, deduplication IDs and delivery state across restarts. A delayed event must not move the activity timestamp backwards. Verify manual-reply synchronization on the actual devices used; an unobserved reply must not silently be treated as seven days of inactivity.

## Notifications and human takeover

Every unique incoming message must remain accessible to Rivaldo. The welcome decision must not control whether a message is saved or routed to him.

Use the Business-app inbox when supported by coexistence and an authenticated ministry inbox/notification channel as configured. If a separate WhatsApp alert is required, configure an authorized recipient distinct from the sender; do not assume a number can notify itself through the API.

Queue owner notification and visitor reply independently so one delivery failure does not discard the other. Retry safely, show failed delivery in the owner interface, and avoid repeating the same alert on webhook retries. Notifications should carry only the minimum preview and a private conversation link where available.

“Speak with Rivaldo” and an observed manual takeover set the conversation to human mode. Suppress queued bot replies while that mode is active. Resume automation only through an explicit owner action.

## Integration work and boundaries

1. Back up and transfer the intended account to the Business app through the supported process; verify coexistence eligibility before selecting a paid connection.
2. Configure official webhook verification, signed-event validation, persistent conversation state and deduplicated delivery.
3. Implement the welcome/menu, seven-day rule, owner notification and manual takeover.
4. Connect the ministry adapter to Mercy's existing Homily, Preaching and Seminar service with private identity and draft persistence.
5. Verify the end-to-end flow in a test environment before activating the ministry number.

Preserve HTTPS and the bridge's HMAC-SHA256 authentication, five-minute timestamp check and nonce replay rejection. The current nonce cache is process-local; shared replay protection is needed before relying on it across multiple workers or instances.

Keep phone numbers, message bodies, private drafts, API tokens and bridge secrets out of repository files and routine logs. Resolve credentials server-side. Retain access controls and minimum necessary storage for pastoral conversations.

The seven-day welcome threshold is independent of WhatsApp's customer-service messaging window. A returning user's new message triggers the greeting; there is no seven-day outbound reminder. Follow current template, consent and messaging-window requirements for any separately initiated messages.

## Acceptance checks for implementation

These checks are requirements for future runtime work, not tests completed by this documentation change.

- [ ] A first contact receives one Jesus-centred greeting and the correct public menu; Rivaldo receives the message.
- [ ] A contact chatting on alternate days never receives a repeated automatic welcome.
- [ ] Boundary checks at 167 hours 59 minutes and 168 hours give the intended result.
- [ ] Silence alone triggers no outbound greeting.
- [ ] A manual reply resets activity, including supported coexistence echoes.
- [ ] Duplicate/reordered events, concurrent messages and a service restart do not repeat a greeting or lose owner delivery.
- [ ] Human takeover suppresses automated replies until explicit resumption.
- [ ] Public visitors can browse published homiletics but cannot generate or retrieve private drafts.
- [ ] Authorized Homily, Preaching and Seminar requests reuse the existing service; missing inputs prompt clarification.
- [ ] Private draft persistence, source preservation, review and explicit publication are verified separately.
- [ ] Bridge authentication and replay rejection work under the intended deployment topology.
- [ ] Existing contacts are initialized without falsely classifying them all as new.
- [ ] Provider failures produce a controlled response or handoff without exposing secrets or falsely claiming success.

## Reference material

Platform documentation checked during planning on 9 October 2026; recheck eligibility and messaging requirements at activation.

- [WhatsApp greeting messages](https://faq.whatsapp.com/501866148528310/?cms_platform=android): the app's built-in repeat interval is 14 days; custom integration is needed for this seven-day rule.
- [Moving from Messenger to the Business app](https://faq.whatsapp.com/3059780464322392/?cms_platform=android&locale=en_US).
- [WhatsApp Business Platform features](https://whatsappbusiness.com/products/business-platform-features/).
- [Coexistence documentation](https://docs.360dialog.com/docs/resources/phone-numbers/coexistence): account eligibility applies; this reference is not a provider purchase decision.
- [WhatsApp Business Messaging Policy](https://whatsappbusiness.com/policy/).

## Completion record for this change

This file records the integration requirements and the existing Homily Service to reuse. Implementation, account onboarding, runtime validation and activation remain pending.
