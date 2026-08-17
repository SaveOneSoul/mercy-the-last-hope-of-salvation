# Mercy Catholic AI Backend

This is the deployable backend for **Mercy – The Last Hope of Salvation**. It is intentionally **Roman Catholic-only**.

## Enforcement layers

1. **Prompt-injection gate** rejects common scope-bypass attempts before generation.
2. **Scope classifier** outputs only `catholic`, `pastoral_safety`, or `out_of_scope`; uncertainty fails closed.
3. **Approved Catholic retrieval** uses only `app/data/catholic_knowledge.json`.
4. **No web-search tool is enabled for the answer model.**
5. **Structured answer schema** requires `catholic_scope_confirmed`, an answer, and approved source IDs.
6. **Post-validation** discards citations not present in retrieved approved sources; no valid source means no generated doctrinal answer.
7. Provider/API failures never fall back to an unrestricted assistant.

The current knowledge base prioritizes Vatican/Catechism material, official CHARIS resources, and the National Shrine of The Divine Mercy. Expand it only with reviewed Catholic sources.

## Run locally

```bash
cd backend
python -m venv .venv
# Windows PowerShell:
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
# Set environment variables (or load .env with your deployment platform).
uvicorn app.main:app --reload --port 8000
```

Then configure the frontend `javascript/config.js`:

```js
apiBaseUrl: "http://localhost:8000",
enableRemoteAI: true
```

## Production

- Put the API behind HTTPS.
- Set `ALLOWED_ORIGINS` to the exact website origin(s).
- Store `OPENAI_API_KEY`, SMTP credentials and WhatsApp access token in a cloud secrets manager.
- Replace SQLite with managed PostgreSQL by setting `DATABASE_URL`.
- Replace the in-memory rate limiter with Redis or an API gateway rate limiter when running multiple instances.
- Add CAPTCHA/Turnstile to the contact form before public launch.
- Add an authenticated admin dashboard before exposing stored prayer requests to staff.
- Publish privacy/retention policies before collecting sensitive prayer requests.

## Catholic-source governance

Recommended source priority:

1. Sacred Scripture and official liturgical texts (using a licensed/approved translation).
2. Ecumenical councils and Vatican documents.
3. Catechism of the Catholic Church.
4. Papal documents and official dicastery material.
5. Episcopal-conference and diocesan sources.
6. Officially recognized Catholic institutions/renewal services for their own approved devotional material.
7. Secondary Catholic scholarship only after editorial review.

Wikipedia should not be placed in the AI doctrine knowledge base. It may remain a human-readable secondary background link on non-doctrinal history pages.
