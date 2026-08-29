# Mercy API

FastAPI backend for **Mercy – The Last Hope of Salvation**. GitHub Pages serves only the static frontend; deploy this folder separately to Cloud Run, Render, Railway, Fly.io, Azure Container Apps, or any Docker host.

## What the API stores

- Prayer intentions submitted through the prayer form.
- Contact-form messages.
- **Save One Soul participation:** anonymous token hash, language (`en` or `kha`), Day 1–7 completion flags, start time and optional completion time.

The Save One Soul tracker does **not** require or store a participant name, phone number, email address, IP address, or the identity of the person being prayed for.

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

Leave either value blank until that service is ready. The frontend will not send tracking requests when `mercy_api_base` is blank and will not load the Cloudflare beacon when the Cloudflare token is blank.

## Save One Soul endpoints

- `POST /api/save-one-soul/join`
- `POST /api/save-one-soul/day`
- `POST /api/save-one-soul/complete`
- `GET /api/save-one-soul/status/{token}`
- `GET /api/save-one-soul/stats`

Public statistics expose aggregate counts only.
