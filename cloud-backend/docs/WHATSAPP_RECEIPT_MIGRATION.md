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
COMMIT;
```

## Rollback (only if no receipts need preserving)

```sql
BEGIN;
DROP INDEX IF EXISTS whatsapp_ministry_outbox_provider_message_id_key;
ALTER TABLE whatsapp_ministry_outbox
  DROP COLUMN IF EXISTS delivery_status,
  DROP COLUMN IF EXISTS provider_message_id;
COMMIT;
```

Do not run rollback if provider IDs or receipt states must be retained.
Back up before migration and confirm table/index ownership and existing
constraints. Migration is **not** yet verified on a staging clone.

## Semantics and limitations

- `status=sent` means Meta's send API accepted the request, not delivery.
- `delivery_status` tracks `sent`, `delivered`, `read`, `failed`.
- Signed receipts only update matching known provider IDs and phone accounts.
- Unknown receipts (including callbacks preceding DB commit) are ignored;
  replay/backfill is **not implemented**. This is an open acceptance gate.
- HTTP timeouts remain `unknown` and are never automatically retried.
- The human handoff in-flight race and scheduled privacy retention remain
  separate unresolved gates.
- Outbound stays disabled and Meta webhook remains unconfigured.
