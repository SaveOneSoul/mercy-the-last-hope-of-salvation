-- Disposable PostgreSQL clone only. Destructive if real receipts exist.
BEGIN;
DROP TABLE IF EXISTS whatsapp_ministry_delivery_receipts;
DROP INDEX IF EXISTS whatsapp_ministry_outbox_provider_message_id_key;
ALTER TABLE whatsapp_ministry_outbox
  DROP COLUMN IF EXISTS delivery_status,
  DROP COLUMN IF EXISTS provider_message_id;
COMMIT;
