-- Disposable PostgreSQL clone only. Destructive if real receipts exist.
-- Dropping the column also removes its dependent UNIQUE constraint/index.
-- Do not DROP INDEX directly: on a fresh ORM schema it is constraint-owned.
BEGIN;
DROP TABLE IF EXISTS whatsapp_ministry_delivery_receipts;
ALTER TABLE whatsapp_ministry_outbox
  DROP COLUMN IF EXISTS delivery_status,
  DROP COLUMN IF EXISTS provider_message_id;
COMMIT;
