# Google Cloud Run deployment

This release is prepared for a low-traffic Cloud Run deployment with the Catholic-only AI guard enabled.

## Recommended first deployment

- Region: `asia-south1` (Mumbai)
- CPU: 1 vCPU
- Memory: 512 MiB
- Minimum instances: 0
- Maximum instances: 3
- Public HTTPS API: enabled (`--allow-unauthenticated`) because GitHub Pages must call it
- OpenAI API key: Google Secret Manager, never browser JavaScript
- Contact DB persistence: disabled until a durable database is attached

## Windows PowerShell

From the project root:

```powershell
cd .\backend

gcloud auth login

gcloud auth application-default login

.\cloudrun\deploy.ps1 `
  -ProjectId "YOUR_GOOGLE_CLOUD_PROJECT_ID" `
  -GitHubOrigin "https://YOUR_GITHUB_USERNAME.github.io"
```

The script:

1. enables the required Google Cloud APIs;
2. creates a dedicated Cloud Run runtime service account;
3. prompts securely for the OpenAI API key if the Secret Manager secret does not exist;
4. grants only Secret Manager accessor permission to the runtime identity;
5. deploys the backend from source;
6. discovers the generated `run.app` URL;
7. writes that public URL into `javascript/config.js` and enables remote AI.

Then test:

```powershell
.\cloudrun\test-api.ps1 -ServiceUrl "https://YOUR-SERVICE-URL.run.app"
```

The test sends both a Catholic question and a non-Catholic programming question and verifies that the latter is rejected.

## Contact form

`/api/chat` can go live immediately once the OpenAI secret is set.

`/api/contact` intentionally refuses to report success until at least one real delivery/persistence path exists:

- SMTP + `OWNER_EMAIL`, or
- WhatsApp Cloud API + `OWNER_WHATSAPP`, or
- `PERSIST_CONTACT_MESSAGES=true` with a durable `DATABASE_URL`.

Do not enable SQLite persistence on Cloud Run for production contact messages because instance-local files are not durable storage.

## Add email later

Use normal environment variables for non-secret settings and Secret Manager for passwords. Required values:

- `OWNER_EMAIL`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_FROM`
- `SMTP_USE_TLS`
- secret: `SMTP_PASSWORD`

## Add WhatsApp later

Required values:

- `OWNER_WHATSAPP`
- `WHATSAPP_API_URL`
- secret: `WHATSAPP_ACCESS_TOKEN`

## Durable database later

Use PostgreSQL (for example Cloud SQL or another managed PostgreSQL provider), set `DATABASE_URL`, then set:

```text
PERSIST_CONTACT_MESSAGES=true
```

Do that only after networking, credentials, migrations, backups and privacy/retention controls are configured.
