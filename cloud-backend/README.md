# Mercy API

FastAPI backend for **Mercy – The Last Hope of Salvation**. GitHub Pages serves only the static frontend; deploy this folder separately to Cloud Run, Render, Railway, Fly.io, Azure Container Apps, or any Docker host.

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

Set `CORS_ORIGINS` to the exact GitHub Pages origin and set `window.MERCY_API_BASE` in the frontend before enabling public form submission. Use managed PostgreSQL in production; keep database credentials in host secrets, never in Git.
