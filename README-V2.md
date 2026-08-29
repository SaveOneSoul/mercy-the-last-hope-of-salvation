# Mercy – The Last Hope of Salvation · V2

Professional Catholic website for GitHub Pages with a cloud-ready FastAPI backend.

## Frontend
- Responsive, accessible, mobile navigation and dark mode
- Divine Mercy landing page with verified St. Faustina quotation
- Save One Soul Campaign
- Searchable saints catalogue
- Complete Rosary guide with 20 mysteries and Litany of Loreto
- Seven Sorrows Servite Rosary
- Divine Mercy Chaplet
- Traditional 33–Our Father Precious Blood Chaplet + litany
- Eucharistic miracles overview
- CHARIS New Life Seminar, Baptism in the Spirit, Duquesne Weekend
- Veni Creator Spiritus and Veni Sancte Spiritus in Latin + fresh English translations
- PWA/offline shell

## Backend
See `cloud-backend/README.md`. The API is not executed by GitHub Pages; deploy it separately and configure `window.MERCY_API_BASE`.

## Sources
See `pages/sources.html`.

## Verification
- Internal links validated locally
- JavaScript syntax checked with Node.js
- FastAPI Python modules syntax-compiled
- CHARIS New Life URL and Duquesne history verified against CHARIS International
- Precious Blood chaplet/litany identified in the Holy See Directory on Popular Piety (§178)
- Seven Sorrows structure cross-checked with the Secular Order of Servants of Mary

## GitHub Pages
The workflow at `.github/workflows/mercy-pages.yml` stages only the static frontend. The existing repository backend remains separate from `cloud-backend/`, which is the V2 cloud deployment package.
