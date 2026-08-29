# Mercy API

FastAPI backend for **Mercy – The Last Hope of Salvation**. GitHub Pages serves only the static frontend; deploy this folder separately to Cloud Run, Render, Railway, Fly.io, Azure Container Apps, or any Docker host.

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
MAGISTERIUM_TIMEOUT_SECONDS=30
MAGISTERIUM_RATE_LIMIT_PER_MINUTE=8
```

Never place `MAGISTERIUM_API_KEY` in `javascript/`, HTML, GitHub Pages configuration, repository secrets printed into a build artifact, or any other public file. On Cloud Run, keep it in Secret Manager and expose it to the container as the `MAGISTERIUM_API_KEY` environment variable.

The Mercy gateway requests non-streaming answers and related questions. It returns the answer plus the Catholic source citations supplied by Magisterium. The system prompt asks for Catholic-only scope, doctrinal distinctions, primary/authoritative sources, and faithful Khasi responses where possible.

The in-memory per-client limiter protects the public gateway from rapid repeated requests. For a large public deployment, add a durable/shared rate limiter or API gateway in front of the service as well.

## Local

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

Set `CORS_ORIGINS` to the exact GitHub Pages origin. Use managed PostgreSQL in production; keep database credentials in host secrets, never in Git. The default SQLite database is for development and is not appropriate for durable production counters on a stateless container platform.

## Connect the live website

Edit `javascript/analytics-config.json` after the backend is deployed:

```json
{
  "mercy_api_base": "https://YOUR-MERCY-API.example",
  "cloudflare_web_analytics_token": "YOUR-CLOUDFLARE-SITE-TOKEN"
}
```

Leave either value blank until that service is ready. The frontend will not send API requests when `mercy_api_base` is blank and will not load the Cloudflare beacon when the Cloudflare token is blank.

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
