# Mercy API

FastAPI backend for **Mercy – The Last Hope of Salvation**. GitHub Pages serves the static frontend; this folder runs separately on Google Cloud Run.

## Production architecture

```text
GitHub Pages
  https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/
        |
        | HTTPS API + CMS content reads
        v
Google Cloud Run
  mercy-api
        |
        +-- Magisterium AI (API key from Secret Manager)
        +-- Password-protected Admin Dashboard / CMS
        |
        +-- Cloud SQL for PostgreSQL
        |     mercy-postgres / mercy
        |     +-- Save One Soul progress
        |     +-- prayer/contact data
        |     +-- CMS editorial overrides
        |
        +-- Cloud Storage
              public website images uploaded through the CMS
```

The static site remains on GitHub Pages. Technical structure, CSS, JavaScript, backend code, security configuration and interactive components remain source-controlled. Normal editorial updates are managed through the Admin Dashboard.

## Admin Dashboard and CMS

After deployment, open:

```text
https://YOUR-CLOUD-RUN-URL/admin
```

The dashboard has two primary areas:

1. **Mission Dashboard** — shows total joined, completed, in-progress, completion rate and recent anonymous participant records.
2. **Content Manager** — edits public-site headings, paragraphs, devotional text, links and images without modifying HTML/CSS/backend source.

### Participant privacy

The Save One Soul campaign remains anonymous by design. The dashboard can show:

- a short anonymous identifier derived from the stored token hash,
- language,
- start timestamp,
- Day 1–7 completion state,
- completion timestamp.

It cannot show a person's name, phone number, email address, IP address, or the identity of the person being prayed for because those values are not collected by the campaign.

### Editorial vs technical changes

The Content Manager intentionally excludes technical DOM subtrees. Any element inside a component carrying a `data-*` attribute, and form/control/script elements, are locked out of editorial editing. This protects features such as:

- Save One Soul tracking,
- Catholic AI,
- prayer/contact forms,
- interactive search/components,
- JavaScript behavior and security controls.

Editorial CMS changes are stored as sanitized field-level overrides in Cloud SQL. The public `javascript/mercy.js` fetches those overrides and applies them to the existing static DOM. The static HTML therefore remains a safe fallback and the technical shell stays version-controlled.

### Image updates

The Admin Dashboard accepts JPG, PNG, WebP and GIF images up to 5 MB. Images are uploaded to the dedicated public CMS asset bucket and the selected page receives the new image URL as a CMS override. SVG uploads are intentionally excluded from the admin uploader.

### Admin security

The deployment script stores these values in Secret Manager and injects them only into Cloud Run:

```text
ADMIN_PASSWORD
ADMIN_SESSION_SECRET
```

The admin password is never committed to GitHub. Admin sessions use a signed, Secure, HttpOnly, SameSite=Strict cookie with an eight-hour expiry. State-changing requests also require a session-bound CSRF token and same-origin validation. Login attempts are rate-limited in-process.

To rotate the dashboard password intentionally:

```powershell
.\deploy-gcp.ps1 -RotateAdminPassword
```

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
- **CMS overrides:** page path, deterministic CSS selector, approved field type and sanitized editorial value.

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

## One-command Google Cloud deployment

From PowerShell in `cloud-backend`, run these as **separate commands**:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\deploy-gcp.ps1
```

The first Admin-CMS deployment asks you to choose a strong admin password (minimum 12 characters). It creates that password as a Secret Manager secret; it does not print or commit it. It also creates a random session-signing secret and the CMS image bucket automatically.

Do **not** append `Set-ExecutionPolicy`, virtual-environment activation, or another parenthesized expression to the script invocation. The deployment script has positional argument binding disabled so an accidental extra expression cannot silently replace the configured Google Cloud project ID.

The default project is:

```text
mercy-last-hope-rk-260817
```

The script is idempotent and will:

1. Enable Cloud Run, Cloud Build, Artifact Registry, Secret Manager, IAM, Cloud SQL and Cloud Storage APIs.
2. Create or reuse the dedicated Cloud Run runtime service account.
3. Create or reuse the Magisterium API-key secret.
4. Create or reuse PostgreSQL Cloud SQL and the `mercy` database/user.
5. Create or reuse the admin-password and session-signing secrets.
6. Create or reuse the CMS image bucket and grant the runtime account object-management permission.
7. Keep CMS images publicly readable because they are public website assets.
8. Attach Cloud SQL to Cloud Run using the authenticated Unix socket.
9. Deploy the API/Admin CMS.
10. Verify database durability, CMS configuration, Save One Soul statistics and Catholic AI connectivity.

To rotate the database password intentionally:

```powershell
.\deploy-gcp.ps1 -RotateDatabasePassword
```

To rotate the admin password intentionally:

```powershell
.\deploy-gcp.ps1 -RotateAdminPassword
```

The default Cloud SQL tier is `db-f1-micro` to keep a small ministry deployment economical.

## Health verification

After production deployment:

```powershell
Invoke-RestMethod https://YOUR-CLOUD-RUN-URL/health | ConvertTo-Json -Depth 8
```

A healthy deployment reports sections similar to:

```json
{
  "database": {
    "backend": "cloud-sql-postgresql",
    "durable": true,
    "reachable": true
  },
  "admin_cms": {
    "configured": true,
    "bucket_configured": true
  }
}
```

## Local development

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8080
```

For local Admin CMS testing, set non-production values for `ADMIN_PASSWORD` and `ADMIN_SESSION_SECRET`. The production values must stay in Secret Manager.

## Connect the live website

The public frontend reads the Cloud Run base URL from `javascript/analytics-config.json`. The same API now serves both campaign functionality and public CMS overrides. Keep `CORS_ORIGINS` restricted to the exact production frontend origin (`https://saveonesoul.github.io`).

## Public endpoints

- `POST /api/chat` — Catholic AI via Magisterium AI
- `POST /api/prayer-intentions`
- `POST /api/contact`
- `POST /api/save-one-soul/join`
- `POST /api/save-one-soul/day`
- `POST /api/save-one-soul/complete`
- `GET /api/save-one-soul/status/{token}`
- `GET /api/save-one-soul/stats`
- `GET /api/content/blocks?path=...` — published CMS editorial overrides
- `GET /health`

The `/admin` interface and `/api/admin/*` routes are protected by the Admin CMS authentication layer. Public Save One Soul statistics expose aggregate counts only.
