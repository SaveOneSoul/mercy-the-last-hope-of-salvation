# Mercy API

FastAPI backend for **Mercy – The Last Hope of Salvation**. GitHub Pages serves the static frontend; this folder runs separately on Google Cloud Run.

## Production architecture

```text
GitHub Pages
  https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/
        |
        | HTTPS API
        v
Google Cloud Run
  mercy-api
        |
        +-- Magisterium AI (API key from Secret Manager)
        |
        +-- Cloud SQL for PostgreSQL
            mercy-postgres / mercy
```

The static site does not need to move into Cloud Run. Its JavaScript calls the public Cloud Run API configured in `javascript/analytics-config.json`.

## Durable data

Production uses Cloud SQL PostgreSQL. The deployment script creates or reuses:

- Cloud SQL instance: `mercy-postgres`
- PostgreSQL database: `mercy`
- Application user: `mercy_app`
- Secret Manager secret: `mercy-db-password`
- Cloud Run Unix-socket attachment for the Cloud SQL instance

The application builds its PostgreSQL connection from `DB_USER`, `DB_PASS`, `DB_NAME`, and `INSTANCE_UNIX_SOCKET`. `DB_PASS` is supplied from Secret Manager. The database password is never committed to GitHub.

For local development only, `DATABASE_URL=sqlite:///./mercy.db` remains supported as a fallback.

## What the API stores

- Prayer intentions submitted through the prayer form.
- Contact-form messages.
- **Save One Soul participation:** anonymous token hash, language (`en` or `kha`), Day 1–7 completion flags, start time and optional completion time.

The Save One Soul tracker does **not** require or store a participant name, phone number, email address, IP address, or the identity of the person being prayed for.

## Magisterium AI

`POST /api/chat` is a server-side gateway to the Magisterium AI Chat Completions API. The browser never receives the Magisterium credential.

Configure these values only on the backend host:

```text
MAGISTERIUM_API_KEY=<secret>
MAGISTERIUM_MODEL=magisterium-1
MAGISTERIUM_CHAT_URL=https://www.magisterium.com/api/v1/chat/completions
MAGISTERIUM_TIMEOUT_SECONDS=90
MAGISTERIUM_RATE_LIMIT_PER_MINUTE=8
```

Never place `MAGISTERIUM_API_KEY` in `javascript/`, HTML, GitHub Pages configuration, repository secrets printed into a build artifact, or any other public file. On Cloud Run, keep it in Secret Manager and expose it to the container as the `MAGISTERIUM_API_KEY` environment variable.

The Mercy gateway requests non-streaming answers and related questions. It returns the answer plus the Catholic source citations supplied by Magisterium. The system prompt asks for Catholic-only scope, doctrinal distinctions, primary/authoritative sources, and faithful Khasi responses where possible.

The in-memory per-client limiter protects the public gateway from rapid repeated requests. For substantially larger traffic, add a durable/shared limiter or API gateway.

## One-command Google Cloud deployment

From PowerShell in `cloud-backend`, run these as **separate commands**:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\deploy-gcp.ps1
```

Do **not** append `Set-ExecutionPolicy`, virtual-environment activation, or another parenthesized expression to the script invocation. The deployment script has positional argument binding disabled so an accidental extra expression cannot silently replace the configured Google Cloud project ID.

The default project is:

```text
mercy-last-hope-rk-260817
```

If you intentionally want to override it, use a named parameter:

```powershell
.\deploy-gcp.ps1 -ProjectId "mercy-last-hope-rk-260817"
```

The Python virtual environment is not required for this deployment command; Cloud Build builds the container from `cloud-backend` using the checked-in `Dockerfile` and `requirements.txt`.

The script is idempotent and will:

1. Enable Cloud Run, Cloud Build, Artifact Registry, Secret Manager, IAM and Cloud SQL Admin APIs.
2. Create or reuse the dedicated Cloud Run runtime service account.
3. Create or reuse the Magisterium API-key secret.
4. Create or reuse a PostgreSQL 15 Cloud SQL instance in `asia-south1`.
5. Create or reuse the `mercy` database and `mercy_app` user.
6. Generate a strong database password when required and store it in Secret Manager.
7. Grant the runtime identity only Cloud SQL Client and secret-access permissions.
8. Attach Cloud SQL to Cloud Run using the authenticated Unix socket.
9. Deploy the API.
10. Verify `/health`, database durability/reachability, Save One Soul statistics, and Catholic AI connectivity.

To rotate the database password intentionally:

```powershell
.\deploy-gcp.ps1 -RotateDatabasePassword
```

The default Cloud SQL tier is `db-f1-micro` to keep a small ministry deployment economical. For greater capacity, pass another supported Cloud SQL tier:

```powershell
.\deploy-gcp.ps1 -DbTier "db-g1-small"
```

## Health verification

After production deployment:

```powershell
Invoke-RestMethod https://YOUR-CLOUD-RUN-URL/health | ConvertTo-Json -Depth 8
```

A healthy durable deployment reports a database section similar to:

```json
{
  "database": {
    "backend": "cloud-sql-postgresql",
    "durable": true,
    "reachable": true
  }
}
```

Then verify aggregate Save One Soul statistics:

```powershell
Invoke-RestMethod https://YOUR-CLOUD-RUN-URL/api/save-one-soul/stats | ConvertTo-Json -Depth 8
```

Finally test the real frontend:

1. Open the Save One Soul page.
2. Click **Join the 7-Day Mission**.
3. Mark **Day 1**.
4. Refresh the browser.
5. Confirm Day 1 remains recorded.
6. A later Cloud Run revision or instance restart should not erase the record because it now resides in Cloud SQL.

## Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

## Docker

```bash
docker compose up --build
```

## Connect the live website

The public frontend currently reads:

```json
{
  "mercy_api_base": "https://YOUR-MERCY-API.example",
  "cloudflare_web_analytics_token": ""
}
```

from `javascript/analytics-config.json`.

Set `mercy_api_base` to the Cloud Run service URL. Keep `CORS_ORIGINS` restricted to the exact production frontend origin (`https://saveonesoul.github.io`).

## Public endpoints

- `POST /api/chat` — Catholic AI via Magisterium AI
- `POST /api/prayer-intentions`
- `POST /api/contact`
- `POST /api/save-one-soul/join`
- `POST /api/save-one-soul/day`
- `POST /api/save-one-soul/complete`
- `GET /api/save-one-soul/status/{token}`
- `GET /api/save-one-soul/stats`
- `GET /health`

Public Save One Soul statistics expose aggregate counts only.
