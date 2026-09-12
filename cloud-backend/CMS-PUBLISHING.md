# Mercy Admin Publishing CMS

Mercy Admin is now both an operations dashboard and a publishing system. Ordinary editorial work should be done here rather than by editing HTML, CSS, JavaScript or backend code.

## Admin entry point

After the Cloud Run backend is deployed:

```text
https://<mercy-cloud-run-service>/admin
```

The admin password is stored in Google Secret Manager (`mercy-admin-password`). The session signing secret is stored separately in `mercy-admin-session-secret`.

## What can be published without code changes

Use **Create** in Mercy Admin for:

- Reflections
- Prayers
- Announcements
- Catholic teaching
- Events
- Testimonies
- News and ministry updates
- Permanent CMS-created pages

Posts support English, Khasi or bilingual English + Khasi content, cover images, featured status, pinned status, drafts, immediate publishing and scheduled publishing.

Permanent pages use the safe block builder. Supported blocks are:

- Heading
- Paragraph
- Image
- Scripture
- Quote
- Callout
- Button/link
- Gallery

## Public publishing flow

```text
Mercy Admin composer
        |
        v
Cloud Run publishing API
        |
        v
Cloud SQL: cms_publications / cms_media
        |
        v
GitHub Pages public renderers
```

Public endpoints:

```text
GET /api/content/posts
GET /api/content/posts/{slug}
GET /api/content/pages/{slug}
```

Public GitHub Pages renderers:

```text
/pages/posts.html
/pages/post.html?slug=<slug>
/pages/content.html?slug=<slug>

/kh/pages/posts.html
/kh/pages/post.html?slug=<slug>
/kh/pages/content.html?slug=<slug>
```

The English and Khasi homepages also load the latest published posts automatically.

## Media Library

Images uploaded through **Media** are stored in the configured Google Cloud Storage CMS bucket. The bucket contains public website assets only. Admin authentication is required to upload files.

Supported uploads:

- JPEG
- PNG
- WebP
- GIF
- Maximum size: 10 MB per image in the publishing Media Library

## Publishing states

- `draft` — private to Admin
- `published` — visible immediately
- `scheduled` — becomes publicly visible when its scheduled timestamp is reached
- `archived` — hidden from the public site but retained in Cloud SQL

Scheduled publication does not need a background worker. Public content queries treat scheduled rows as visible when `scheduled_at <= current time`.

## Existing technical pages

The **Existing Pages** editor remains available for ordinary wording, link and image changes to static site pages. Interactive `data-*` components, forms, scripts and application controls are excluded from that editor.

## Technical-only changes

Repository/code changes remain appropriate for:

- security controls
- authentication
- database schema
- API behavior
- Catholic AI integration
- Save One Soul tracking logic
- JavaScript application behavior
- CSS/layout architecture
- service worker/PWA logic
- deployment infrastructure

New ordinary content should not require a repository deployment.

## Deployment

From the repository root:

```powershell
cd .\cloud-backend
Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned -Force
.\deploy-gcp.ps1
```

The deployment script reuses the existing Cloud SQL instance, database, runtime service account and secrets. If the Admin secrets or CMS image bucket do not yet exist, it creates them.

After deployment, `/health` should report API version `2.5.0` and:

```json
{
  "admin_cms": {
    "configured": true,
    "bucket_configured": true,
    "publishing_enabled": true
  }
}
```

The new `cms_publications` and `cms_media` tables are created automatically by SQLAlchemy on first startup. Existing Save One Soul data remains untouched.
