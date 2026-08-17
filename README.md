# Mercy – The Last Hope of Salvation

A responsive, multi-page Catholic website designed to run immediately on **GitHub Pages**
and later migrate to a professional cloud backend.

## Included pages

1. Divine Mercy
2. Pages / Resources of Divine Mercy
3. Chaplet of Divine Mercy
4. Holy Rosary — all four sets of mysteries
5. Seven Sorrows of Our Lady
6. Eucharistic Miracles
7. Saints of the Church
8. Bible
9. Catechism of the Catholic Church — CCC + Scripture cross-references
10. Holy Spirit & Baptism in the Holy Spirit
11. Save One Soul Campaign
12. Catholic Charismatic Renewal
13. Prayer Requests & Contact

## Folder structure

```text
mercy-last-hope-salvation/
├─ index.html
├─ .nojekyll
├─ html/
│  ├─ divine-mercy.html
│  ├─ pages-of-divine-mercy.html
│  ├─ chaplet.html
│  ├─ holy-rosary.html
│  ├─ seven-sorrows.html
│  ├─ eucharistic-miracles.html
│  ├─ saints.html
│  ├─ bible.html
│  ├─ holy-spirit.html
│  ├─ save-one-soul.html
│  ├─ charismatic-renewal.html
│  └─ contact.html
├─ css/
│  └─ style.css
├─ javascript/
│  ├─ config.js
│  ├─ main.js
│  └─ chatbot.js
├─ assets/
│  └─ images/
└─ backend-example/
   └─ README.md
```

## Configure email or WhatsApp for GitHub Pages

Open:

`javascript/config.js`

Then set either or both:

```js
contactEmail: "YOUR_EMAIL@example.com",
whatsappNumber: "91XXXXXXXXXX"
```

The WhatsApp number must use international format with digits only.

### Important limitation

GitHub Pages is static hosting. It cannot safely hold secret API keys and cannot itself
send SMTP email, call the WhatsApp Business API with a secret token, or securely call
OpenAI/Gemini.

The static contact form therefore:

1. tries `POST /api/contact` when `apiBaseUrl` is configured;
2. otherwise opens the visitor's email client if `contactEmail` is configured;
3. otherwise opens WhatsApp if `whatsappNumber` is configured.

The chatbot works locally with a small catechetical FAQ knowledge base. For real AI,
deploy a backend and configure `/api/chat`.

## Deploy to GitHub Pages

1. Create a new GitHub repository, for example `mercy-last-hope-salvation`.
2. Upload the **contents of this folder** to the repository root.
3. Commit and push.
4. Open **Repository Settings → Pages**.
5. Under **Build and deployment**, choose **Deploy from a branch**.
6. Select the `main` branch and `/ (root)`.
7. Save. GitHub will publish the site.

## Recommended professional-cloud phase

A later production architecture can use:

- Frontend: current HTML/CSS/JS or migrate to Next.js/React
- API: FastAPI or Node.js
- Database: PostgreSQL
- Admin: authenticated content management
- Email: Resend / Postmark / SendGrid / SMTP
- WhatsApp: Meta WhatsApp Business Cloud API
- AI: server-side OpenAI API with retrieval from approved Catholic sources
- Files/media: S3-compatible object storage
- CDN/WAF: Cloudflare
- Hosting: AWS, Azure, Google Cloud, Render, Railway, Fly.io, Vercel or similar
- Observability: logs, error monitoring, uptime monitoring
- Security: HTTPS, CSP, rate limiting, CAPTCHA, secure cookies, secrets manager, backups

## Content-source policy

The site paraphrases and points visitors to authoritative sources instead of copying
long copyrighted texts.

Primary references used in this starter include:

- Dives in Misericordia: https://www.vatican.va/content/john-paul-ii/en/encyclicals/documents/hf_jp-ii_enc_30111980_dives-in-misericordia.html
- Catechism of the Catholic Church: https://www.vatican.va/archive/ccc/index.htm
- Dei Verbum: https://www.vatican.va/archive/hist_councils/ii_vatican_council/documents/vat-ii_const_19651118_dei-verbum_en.html
- Rosarium Virginis Mariae: https://www.vatican.va/content/john-paul-ii/en/apost_letters/2002/documents/hf_jp-ii_apl_20021016_rosarium-virginis-mariae.html
- National Shrine of The Divine Mercy — Chaplet: https://thedivinemercy.org/message/devotions/pray-the-chaplet
- CHARIS International: https://www.charis.international/
- CHARIS — Baptism in the Holy Spirit: https://www.charis.international/en/baptism-holy-spirit/
- Pope Leo XIV to members of Catholic Charismatic Renewal (30 May 2026): https://www.vatican.va/content/leo-xiv/en/speeches/2026/may/documents/20260530-carismatici.html
- Dicastery for the Causes of Saints: https://www.vatican.va/content/romancuria/en/dicasteri/dicastero-cause-santi/profilo.html
- USCCB Bible: https://bible.usccb.org/bible

Wikipedia is used only as a secondary background source where an official page is not
practical for a specific devotional-history summary.

## Before public production

Add:
- your real contact email/WhatsApp number;
- a Privacy Policy and Terms page;
- cookie/analytics disclosure if analytics are enabled;
- a safeguarding/contact escalation policy;
- image licences and attribution for any photos you add;
- a backend before enabling genuine AI or collecting prayer requests in a database.



## AI Upgrade: Catholic-only automatic response system

The project now includes `backend/`, a deployable FastAPI service with:

- `POST /api/chat` — Catholic-only AI chat;
- `POST /api/contact` — stores messages and creates automatic replies;
- strict Catholic-scope classification;
- prompt-injection rejection;
- retrieval only from an editorially reviewed Catholic knowledge JSON file;
- structured OpenAI Responses API output and source-ID validation;
- fixed refusal for non-Catholic questions;
- pastoral-safety escalation instead of pretending to replace clergy/professionals;
- email owner notifications and email auto-replies when SMTP is configured;
- optional WhatsApp Cloud API text acknowledgements when configured;
- SQLite by default and PostgreSQL through `DATABASE_URL`;
- Dockerfile and environment template for cloud deployment.

The backend defaults to `gpt-5.6-luna` for cost-sensitive/high-volume catechetical use. The model ID is configurable by environment variable. **No API key belongs in the GitHub Pages frontend.**

See `backend/README.md` and `backend/.env.example`.

---

## Google Cloud Run deployment (AI backend)

The `backend/cloudrun/` folder contains deployment automation for Google Cloud Run.

On Windows PowerShell:

```powershell
cd backend
gcloud auth login
.\cloudrun\deploy.ps1 -ProjectId "YOUR_PROJECT_ID" -GitHubOrigin "https://YOUR_GITHUB_USERNAME.github.io"
```

After deployment, the script automatically updates `javascript/config.js` with the generated Cloud Run URL and enables the remote Catholic-only AI. See `backend/cloudrun/README.md` for details.


## CCC + Bible cross-reference engine

The backend now contains `backend/app/data/catholic_reference_map.json`. Mercy AI retrieves from this approved map and is instructed to use only the supplied Scripture references and CCC paragraph ranges. The public `html/catechism.html` page exposes the same study map. This project intentionally stores paragraph references and concise summaries rather than republishing the complete Catechism text.
