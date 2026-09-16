# Source Code Repository

> ## Official Save One Soul Website
>
> https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/
>
> This repository contains the source code, deployment configuration, backend services, tests, documentation, and development assets for the Save One Soul website.
>
> Visitors looking for the public Catholic mission website should use the official website above.

## Development overview

This project is deployed with a static GitHub Pages frontend and a separate secure cloud backend for dynamic features.

- **Frontend:** HTML, CSS, and JavaScript served through GitHub Pages
- **Backend:** FastAPI service under `backend/`
- **Data:** reviewed application data and reference mappings stored with the backend
- **Deployment:** GitHub Pages for the public frontend and Google Cloud Run support for the backend
- **Automation:** GitHub Actions workflows under `.github/workflows/`
- **Security:** secrets remain server-side; no API key belongs in the GitHub Pages frontend

## Project structure

```text
mercy-the-last-hope-of-salvation/
├─ index.html
├─ pages/
├─ kh/
├─ css/
├─ javascript/
├─ assets/
├─ backend/
├─ .github/workflows/
├─ sitemap.xml
├─ robots.txt
└─ README.md
```

## Frontend configuration

For local/static contact configuration, review:

`javascript/config.js`

GitHub Pages is static hosting. It cannot safely store secret API keys or credentials and must not directly contain SMTP passwords, WhatsApp Business access tokens, or AI-provider secrets.

When a secure backend is configured, frontend requests should be routed to the deployed API rather than embedding credentials in browser code.

## Backend

The `backend/` directory contains the deployable FastAPI application and supporting configuration.

Current backend capabilities include:

- `POST /api/chat`
- `POST /api/contact`
- server-side AI-provider integration
- request validation and scope controls
- source/reference validation
- persistence through SQLite by default or PostgreSQL through `DATABASE_URL`
- optional email and WhatsApp integrations
- Docker support
- Google Cloud Run deployment automation

See `backend/README.md` and `backend/.env.example` for backend-specific setup.

## GitHub Pages deployment

The public frontend is published from this repository through GitHub Pages.

Repository settings should use:

1. **Settings → Pages**
2. **Deploy from a branch**
3. Branch: `main`
4. Folder: `/ (root)`

The official public site is:

https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/

## Google Cloud Run deployment

The `backend/cloudrun/` directory contains deployment automation for the API backend.

Example on Windows PowerShell:

```powershell
cd backend
gcloud auth login
.\cloudrun\deploy.ps1 -ProjectId "YOUR_PROJECT_ID" -GitHubOrigin "https://saveonesoul.github.io"
```

After deployment, configure the frontend to use the generated backend URL according to the backend deployment documentation.

## Security requirements

- Never commit production secrets or API keys.
- Keep privileged integrations behind the backend.
- Validate and sanitize external input.
- Keep dependencies and GitHub Actions pinned and reviewed.
- Use HTTPS-only production endpoints.
- Apply least-privilege permissions to cloud and repository credentials.
- Review authentication, rate limiting, logging, and abuse controls before enabling public write operations.

## Content and licensing

Public-facing editorial content, source references, and attribution belong on the official website and its dedicated source/editorial pages. Repository documentation should remain focused on development, deployment, maintenance, security, and implementation details.

## Production notes

Before enabling new production integrations, verify:

- privacy and terms documentation;
- safeguarding/contact escalation procedures;
- image and media licensing;
- backend configuration and secret storage;
- monitoring and error reporting;
- database backup and recovery procedures;
- deployment and rollback procedures.
