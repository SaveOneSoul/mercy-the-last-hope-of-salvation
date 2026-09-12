import os
from datetime import datetime, timezone
from urllib.parse import quote

from fastapi import APIRouter, Depends, Response
from sqlalchemy import and_, or_
from sqlalchemy.orm import Session

from .db import get_db
from .models import CMSPublication

router = APIRouter()

PUBLIC_SITE_BASE = os.getenv(
    "PUBLIC_SITE_BASE",
    "https://saveonesoul.github.io/mercy-the-last-hope-of-salvation",
).rstrip("/")


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _visible_filter():
    now = _now()
    return or_(
        CMSPublication.status == "published",
        and_(
            CMSPublication.status == "scheduled",
            CMSPublication.scheduled_at.isnot(None),
            CMSPublication.scheduled_at <= now,
        ),
    )


def _url_for(row: CMSPublication, language: str) -> str:
    prefix = "/kh/pages" if language == "kha" else "/pages"
    template = "post.html" if row.kind == "post" else "content.html"
    return f"{PUBLIC_SITE_BASE}{prefix}/{template}?slug={quote(row.slug, safe='')}"


def _languages(row: CMSPublication) -> list[str]:
    if row.language_mode == "both":
        return ["en", "kha"]
    if row.language_mode == "kha":
        return ["kha"]
    return ["en"]


@router.get("/api/content/seo-manifest")
def seo_manifest(response: Response, db: Session = Depends(get_db)):
    """Return indexable URLs for all currently public CMS publications.

    GitHub Pages consumes this endpoint on an hourly deployment schedule and merges
    these URLs into the site's root sitemap.xml. Drafts, archived content, and future
    scheduled content are deliberately excluded.
    """
    response.headers["Cache-Control"] = "no-store, max-age=0"
    rows = (
        db.query(CMSPublication)
        .filter(_visible_filter())
        .order_by(CMSPublication.updated_at.desc(), CMSPublication.id.desc())
        .all()
    )
    items = []
    for row in rows:
        changed = row.updated_at or row.published_at or row.scheduled_at or row.created_at
        for language in _languages(row):
            title = (
                (row.title_kha if language == "kha" else row.title_en)
                or row.title_en
                or row.title_kha
                or "Untitled"
            )
            items.append(
                {
                    "publication_id": row.id,
                    "kind": row.kind,
                    "content_type": row.content_type,
                    "slug": row.slug,
                    "language": language,
                    "title": title,
                    "url": _url_for(row, language),
                    "lastmod": changed.isoformat() if changed else None,
                }
            )
    return {
        "site": PUBLIC_SITE_BASE,
        "generated_at": _now(),
        "items": items,
        "count": len(items),
    }
