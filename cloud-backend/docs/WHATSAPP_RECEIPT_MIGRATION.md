# WhatsApp delivery receipt migration — deployment blocked

The application model now requires two nullable columns on
`whatsapp_ministry_outbox`. SQLAlchemy `create_all()` does **not**
add columns to an existing table. Do not deploy before running and
verifying this migration on a disposable clone of the staging database.

## Forward migration (PostgreSQL)

```sql
BEGIN;
ALTER TABLE whatsapp_ministry_outbox
  ADD COLUMN IF NOT EXISTS provider_message_id VARCHAR(200),
  ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(24);
CREATE UNIQUE INDEX IF NOT EXISTS
  whatsapp_ministry_outbox_provider_message_id_key
  ON whatsapp_ministry_outbox (provider_message_id);
CREATE TABLE IF NOT EXISTS whatsapp_ministry_delivery_receipts (
  id SERIAL PRIMARY KEY,
  account_id VARCHAR(120) NOT NULL,
  provider_message_id VARCHAR(200) NOT NULL,
  delivery_status VARCHAR(24) NOT NULL,
  received_at TIMESTAMPTZ NOT NULL,
  UNIQUE (account_id, provider_message_id)
);
COMMIT;
```

## Rollback (only if no receipts need preserving)

```sql
BEGIN;
DROP TABLE IF EXISTS whatsapp_ministry_delivery_receipts;
ALTER TABLE whatsapp_ministry_outbox
  DROP COLUMN IF EXISTS delivery_status,
  DROP COLUMN IF EXISTS provider_message_id;
COMMIT;
```

Dropping `provider_message_id` automatically removes its dependent unique index or constraint. Do not explicitly drop the index: ORM-created schemas can own it through a UNIQUE constraint. Do not run rollback if provider IDs or receipt states must be retained.
Back up before migration and confirm table/index ownership and existing
constraints. Migration is **not** yet verified on a staging clone.

## Semantics and limitations

- `status=sent` means Meta's send API accepted the request, not delivery.
- `delivery_status` tracks `sent`, `delivered`, `read`, `failed`.
- Signed receipts only update matching known provider IDs and phone accounts.
- Unmatched signed receipts are buffered by provider ID and phone account.
  When a worker records the send response, it consumes the buffered state.
- Unmatched receipts require a bounded cleanup/abuse policy and replay tests
  under concurrent callbacks before activation. No cleanup scheduler exists yet.
- HTTP timeouts remain `unknown` and are never automatically retried.
- The human handoff in-flight race and scheduled privacy retention remain
  separate unresolved gates.
- Outbound stays disabled and Meta webhook remains unconfigured.

## Unmatched receipt maintenance

`purge_expired_delivery_receipts(db, now=...)` removes unmatched receipts older than 7 days. This is **manual and unscheduled**; operational scheduling, metrics, and retention policy approval are still required. Parallel unknown-ID callbacks use a PostgreSQL transaction-scoped advisory lock. Do not treat these additions as permission to activate the webhook.


## Privacy and legacy-schema review (pre-activation)

The integration suite now exercises forward migration twice, rollback, and
forward migration again in a disposable PostgreSQL schema that starts with
a **legacy outbox table without receipt columns**. It asserts that existing
outbox identifiers, job status, and foreign-key reference values survive.
This synthetic legacy fixture does **not** replace a migration rehearsal on
a disposable clone of the actual staging database.

Message retention defaults to 30 days and applies only when all associated
outbox jobs are terminal. Unknown, sending, and pending jobs are deliberately
preserved to avoid losing unreconciled delivery evidence. Conversation
`last_human_at` and `history_known` are retained separately so the seven-day
welcome rule continues to work after old message bodies are removed.
Unmatched receipt retention defaults to 7 days. Neither cleanup operation
is scheduled or enabled automatically.

**Unresolved approval gates:** owner-approved retention/deletion policy,
documented operator cleanup schedule and audit trail, review of retained
contact identifiers and conversation activity metadata, administrator access
review, and migration rehearsal on a disposable staging clone. Rollback
destroys receipt metadata and must not be used after real receipts exist
without a separately approved preservation/recovery plan.

Keep PR in Draft, outbound disabled, and Meta webhook unconfigured.
