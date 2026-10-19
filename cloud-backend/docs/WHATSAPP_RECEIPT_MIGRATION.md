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


## Proposed maintenance runbook — NOT AUTHORIZED FOR EXECUTION

**Prerequisites:** Explicit owner approval of retention periods and operator
access; verified backup/restore; scheduled maintenance window; database
permissions restricted to the WhatsApp tables; audit trail recording time,
operator, affected row counts, and errors. No live or staging cleanup has
been run. Do not run cleanup from a public request handler.

1. Use a disposable database clone to inspect age distributions and count
   inbound records eligible for removal, excluding any with unresolved
   `pending`, `sending`, or `unknown` outbox work. Separately count
   unmatched delivery receipts older than seven days.
2. Confirm no incident investigation, legal hold, or owner-approved
   preservation requirement applies. Review `last_human_at` and
   `history_known` separately; these fields are not removed by message
   cleanup because the seven-day greeting rule needs them.
3. Rehearse both cleanup functions within explicit database transactions on
   the disposable clone, verify counts and referential integrity, and test
   rollback on injected failure.
4. Only after owner approval, establish a narrowly scoped maintenance job
   with least-privilege credentials, bounded execution time, monitoring, and
   alerts for failures. Record aggregate counts rather than message bodies
   or provider identifiers in routine logs.
5. Review retained phone/contact identifiers, access logs, backup expiry,
   data-subject deletion workflows, and the effect of terminal `sent`
   jobs on future receipt reconciliation before production activation.

**Current state:** cleanup functions exist but are manual, no scheduler is
configured, and this document does not authorize deleting user data.


## Owner retention-policy approval — 2026-10-14

The project owner explicitly approved **30-day message-record retention**
and **7-day unmatched-delivery-receipt retention**. The existing safety
exceptions remain mandatory: do not purge inbound messages associated
with pending, sending, or unknown jobs; preserve conversation activity
metadata required for the seven-day greeting/inactivity rule.

This is **policy approval only**, not authorization to execute deletion,
schedule cleanup, run migrations against staging, connect Meta, enable
outbound sends, merge this draft PR, or deploy. A separate operational
security review and explicit staging-deployment approval are required.


## Administrator access and deletion security review — 2026-10-14

The current WhatsApp owner endpoints depend on the existing CMS
`require_admin` signed-session verification. State-changing owner
endpoints also call `_require_write_guard` for CSRF-token validation and
Origin checking when an Origin header is present. Automated regression
tests assert that every WhatsApp admin route has an admin dependency,
every mutating route calls the write guard, and no WhatsApp admin route
exposes HTTP DELETE. These are code-level controls, **not** proof that
production account permissions, session-secret rotation, or operational
access logging have been audited.

**Deletion procedure (not enabled):** The operator must document the
request or scheduled retention basis; identify and exclude pending,
sending, and unknown jobs; preserve seven-day greeting timestamps;
take and test a backup on a disposable clone; record aggregate row
counts before/after; and verify that the process cannot remove data
under preservation hold. Deletion of individual conversations,
associated outbox rows, and identifiers is not yet implemented as a
reviewed user-request workflow. Backups and application logs need
separate expiry/deletion procedures.

**Remaining security gates:** inspect actual staging IAM and admin
access, review audit-log coverage and secret rotation, design
data-subject deletion/backup-expiry handling, and rehearse migration
on a disposable clone of the real staging database. No operational
deletion or deployment is authorized by this review.


## Actual Cloud SQL schema inspection — read-only gate (pending)

GitHub Actions PostgreSQL **15** migration/security suite passed at commit
`4f3b50ea671a41329caf5731bf186fbca298dcb3`. This is a disposable
synthetic schema test, **not** inspection of the actual Cloud SQL database.

To verify real-schema compatibility without a paid clone, an authorized
operator may run the following **read-only metadata queries** against the
existing `mercy` database using a read-only account and an approved secure
connection. Do not run migrations, `CREATE`, `ALTER`, `DROP`, `DELETE`,
or any application tests against this database. Do not export data rows,
message bodies, passwords, connection strings, or credentials.

```sql
SELECT current_database(), current_setting('server_version') AS server_version;
SELECT table_schema, table_name
FROM information_schema.tables
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND table_name LIKE 'whatsapp_ministry_%'
ORDER BY table_schema, table_name;
SELECT table_schema, table_name, column_name, data_type,
       character_maximum_length, is_nullable
FROM information_schema.columns
WHERE table_schema NOT IN ('pg_catalog', 'information_schema')
  AND table_name LIKE 'whatsapp_ministry_%'
ORDER BY table_schema, table_name, ordinal_position;
SELECT n.nspname AS schema_name, t.relname AS table_name,
       c.conname AS constraint_name, c.contype AS constraint_type,
       pg_get_constraintdef(c.oid) AS definition
FROM pg_constraint c
JOIN pg_class t ON t.oid = c.conrelid
JOIN pg_namespace n ON n.oid = t.relnamespace
WHERE n.nspname NOT IN ('pg_catalog', 'information_schema')
  AND t.relname LIKE 'whatsapp_ministry_%'
ORDER BY schema_name, table_name, constraint_name;
```

The results should be reviewed for pre-existing WhatsApp tables, column
types, unique constraints, and unexpected dependencies before authorizing
any real-schema migration. An empty table list is a meaningful result:
there is no legacy WhatsApp schema to migrate in that database. Never
infer from an empty list that the deployment is approved.

If a read-only account or secure connection is not available, stop and
request an access plan. Never use production admin credentials in CI.


## Pre-staging access and deletion decision record — 2026-10-19

**CI verified:** commit `7dcf63f4725a667fc2e0c35e677ed608b453944a`
passed Public Form Audit #711, Mercy Backend Smoke #372, and
WhatsApp PostgreSQL 15 Security Integration #37.

**Read-only schema inspection: NOT EXECUTED.** The repository has no
authorized Cloud SQL connection in this review session. An operator
must confirm a secure access method and a database identity with
SELECT-only metadata permissions. Never grant broad database access
to GitHub Actions or put Cloud SQL credentials in CI. A successful
metadata inspection is evidence of schema compatibility only; it is
not permission to migrate.

**Administrator access findings:** WhatsApp owner routes use the
shared CMS admin session; mutating routes use the existing CSRF
guard. Route-level regression tests passed. This does not establish
individual administrator attribution, least-privilege role separation,
production IAM configuration, secret rotation, or audit-log coverage.
Those controls remain operational acceptance gates.

**Deletion findings:** Owner-approved 30-day inbound and 7-day
unmatched-receipt periods are implemented as manual helper functions,
not a scheduled job. Unresolved pending/sending/unknown work is
excluded; seven-day greeting metadata persists. No reviewed
individual-request erasure workflow, backup-expiry enforcement, or
deletion audit job is present. These are outstanding privacy
requirements before production activation.

**Decision:** Staging deployment, cleanup execution, Meta webhook
configuration, outbound activation, and PR merge are NOT authorized.
Separate owner approval is required after the access and migration
evidence is reviewed.
