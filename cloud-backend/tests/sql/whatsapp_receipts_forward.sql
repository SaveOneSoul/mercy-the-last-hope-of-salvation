-- Disposable PostgreSQL clone only. Not for production execution.
BEGIN;
ALTER TABLE whatsapp_ministry_outbox
  ADD COLUMN IF NOT EXISTS provider_message_id VARCHAR(200),
  ADD COLUMN IF NOT EXISTS delivery_status VARCHAR(24);
CREATE UNIQUE INDEX IF NOT EXISTS whatsapp_ministry_outbox_provider_message_id_key
  ON whatsapp_ministry_outbox(provider_message_id);
CREATE TABLE IF NOT EXISTS whatsapp_ministry_delivery_receipts (
  id SERIAL PRIMARY KEY,
  account_id VARCHAR(120) NOT NULL,
  provider_message_id VARCHAR(200) NOT NULL,
  delivery_status VARCHAR(24) NOT NULL,
  received_at TIMESTAMPTZ NOT NULL,
  UNIQUE (account_id, provider_message_id)
);
COMMIT;
