import json
import os
import re
import unicodedata
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse

import bleach
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, Response, UploadFile
from google.cloud import storage
from pydantic import BaseModel, Field
from sqlalchemy import and_, func, or_
from sqlalchemy.orm import Session

from .cms_admin import _require_write_guard, require_admin
from .db import get_db
from .models import CMSMedia, CMSPublication

router = APIRouter()

CONTENT_TYPES = {
    "reflection",
    "prayer",
    "announcement",
    "catholic-teaching",
    "event",
    "testimony",
    "news",
    "page",
}
POST_CONTENT_TYPES = CONTENT_TYPES - {"page"}
STATUSES = {"draft", "published", "scheduled", "archived"}
LANGUAGE_MODES = {"en", "kha", "both"}
BLOCK_TYPES = {"heading", "paragraph", "image", "quote", "scripture", "callout", "button", "gallery"}

RICH_TAGS = [
    "p", "h2", "h3", "h4", "ul", "ol", "li", "blockquote", "a", "strong",
    "em", "b", "i", "br", "hr", "span", "small", "sup", "sub",
]
RICH_ATTRS = {
    "a": ["href", "target", "rel", "title"],
    "span": ["class"],
}
RICH_PROTOCOLS = ["http", "https", "mailto", "tel"]


class PublicationIn(BaseModel):
    kind: str = Field(default="post", pattern="^(post|page)$")
    content_type: str = Field(default="reflection", max_length=40)
    slug: str | None = Field(default=None, max_length=180)
    status: str = Field(default="draft", pattern="^(draft|published|scheduled|archived)$")
    language_mode: str = Field(default="en", pattern="^(en|kha|both)$")

    title_en: str | None = Field(default=None, max_length=240)
    title_kha: str | None = Field(default=None, max_length=240)
    summary_en: str | None = Field(default=None, max_length=1200)
    summary_kha: str | None = Field(default=None, max_length=1200)
    body_en: str | None = Field(default=None, max_length=100000)
    body_kha: str | None = Field(default=None, max_length=100000)
    blocks_en: list[dict] = Field(default_factory=list)
    blocks_kha: list[dict] = Field(default_factory=list)

    cover_image_url: str | None = Field(default=None, max_length=3000)
    cover_image_alt_en: str | None = Field(default=None, max_length=500)
    cover_image_alt_kha: str | None = Field(default=None, max_length=500)
    featured: bool = False
    pinned: bool = False
    scheduled_at: datetime | None = None


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _clean_text(value: str | None, limit: int | None = None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value:
        return None
    if limit is not None:
        value = value[:limit]
    return value


def _clean_rich(value: str | None) -> str | None:
    value = _clean_text(value)
    if value is None:
        return None
    return bleach.clean(
        value,
        tags=RICH_TAGS,
        attributes=RICH_ATTRS,
        protocols=RICH_PROTOCOLS,
        strip=True,
    )


def _safe_url(value: str | None, *, image: bool = False) -> str | None:
    value = _clean_text(value, 3000)
    if value is None:
        return None
    if value.startswith(("/", "./", "../", "#")) and not image:
        return value
    parsed = urlparse(value)
    if image:
        if parsed.scheme != "https":
            raise HTTPException(status_code=400, detail="image_url_must_use_https")
    elif parsed.scheme not in {"http", "https", "mailto", "tel"}:
        raise HTTPException(status_code=400, detail="unsupported_link_scheme")
    return value


def _slugify(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_value = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "-", ascii_value).strip("-")
    return slug[:160] or f"content-{uuid.uuid4().hex[:10]}"


def _unique_slug(db: Session, desired: str, exclude_id: int | None = None) -> str:
    base = _slugify(desired)
    candidate = base
    number = 2
    while True:
        query = db.query(CMSPublication.id).filter(CMSPublication.slug == candidate)
        if exclude_id is not None:
            query = query.filter(CMSPublication.id != exclude_id)
        if query.first() is None:
            return candidate
        candidate = f"{base[:150]}-{number}"
        number += 1


def _safe_blocks(items: list[dict]) -> list[dict]:
    if len(items) > 100:
        raise HTTPException(status_code=400, detail="too_many_page_blocks")
    clean: list[dict] = []
    for raw in items:
        if not isinstance(raw, dict):
            continue
        block_type = str(raw.get("type", "")).strip().lower()
        if block_type not in BLOCK_TYPES:
            raise HTTPException(status_code=400, detail=f"unsupported_block_type:{block_type}")

        if block_type == "heading":
            text = _clean_text(str(raw.get("text", "")), 500)
            if text:
                level = int(raw.get("level", 2) or 2)
                clean.append({"type": "heading", "text": text, "level": 3 if level == 3 else 2})
        elif block_type in {"paragraph", "callout"}:
            text = _clean_text(str(raw.get("text", "")), 12000)
            if text:
                clean.append({"type": block_type, "text": text})
        elif block_type == "quote":
            text = _clean_text(str(raw.get("text", "")), 8000)
            if text:
                clean.append({
                    "type": "quote",
                    "text": text,
                    "citation": _clean_text(str(raw.get("citation", "")), 500) or "",
                })
        elif block_type == "scripture":
            text = _clean_text(str(raw.get("text", "")), 8000)
            if text:
                clean.append({
                    "type": "scripture",
                    "text": text,
                    "reference": _clean_text(str(raw.get("reference", "")), 300) or "",
                })
        elif block_type == "image":
            url = _safe_url(str(raw.get("url", "")), image=True)
            if url:
                clean.append({
                    "type": "image",
                    "url": url,
                    "alt": _clean_text(str(raw.get("alt", "")), 500) or "",
                    "caption": _clean_text(str(raw.get("caption", "")), 1000) or "",
                })
        elif block_type == "button":
            label = _clean_text(str(raw.get("label", "")), 200)
            href = _safe_url(str(raw.get("href", "")))
            if label and href:
                clean.append({"type": "button", "label": label, "href": href})
        elif block_type == "gallery":
            gallery = []
            for item in list(raw.get("items") or [])[:12]:
                if not isinstance(item, dict):
                    continue
                url = _safe_url(str(item.get("url", "")), image=True)
                if url:
                    gallery.append({
                        "url": url,
                        "alt": _clean_text(str(item.get("alt", "")), 500) or "",
                    })
            if gallery:
                clean.append({"type": "gallery", "items": gallery})
    return clean


def _parse_blocks(value: str | None) -> list[dict]:
    try:
        data = json.loads(value or "[]")
        return data if isinstance(data, list) else []
    except Exception:
        return []


def _plain_summary(html: str | None) -> str:
    if not html:
        return ""
    text = bleach.clean(html, tags=[], strip=True)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:360]


def _localized(row: CMSPublication, language: str) -> dict:
    use_kha = language == "kha"
    title = (row.title_kha if use_kha else row.title_en) or row.title_en or row.title_kha or "Untitled"
    body = (row.body_kha if use_kha else row.body_en) or row.body_en or row.body_kha or ""
    summary = (row.summary_kha if use_kha else row.summary_en) or row.summary_en or row.summary_kha or _plain_summary(body)
    blocks = _parse_blocks(row.blocks_kha_json if use_kha else row.blocks_en_json)
    if not blocks:
        blocks = _parse_blocks(row.blocks_en_json or row.blocks_kha_json)
    alt = (row.cover_image_alt_kha if use_kha else row.cover_image_alt_en) or row.cover_image_alt_en or row.cover_image_alt_kha or ""
    return {
        "id": row.id,
        "kind": row.kind,
        "content_type": row.content_type,
        "slug": row.slug,
        "status": row.status,
        "language": language,
        "language_mode": row.language_mode,
        "title": title,
        "summary": summary,
        "body": body,
        "blocks": blocks,
        "cover_image_url": row.cover_image_url,
        "cover_image_alt": alt,
        "featured": bool(row.featured),
        "pinned": bool(row.pinned),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "published_at": row.published_at or row.scheduled_at or row.created_at,
        "scheduled_at": row.scheduled_at,
    }


def _admin_publication(row: CMSPublication) -> dict:
    return {
        "id": row.id,
        "kind": row.kind,
        "content_type": row.content_type,
        "slug": row.slug,
        "status": row.status,
        "language_mode": row.language_mode,
        "title_en": row.title_en,
        "title_kha": row.title_kha,
        "summary_en": row.summary_en,
        "summary_kha": row.summary_kha,
        "body_en": row.body_en,
        "body_kha": row.body_kha,
        "blocks_en": _parse_blocks(row.blocks_en_json),
        "blocks_kha": _parse_blocks(row.blocks_kha_json),
        "cover_image_url": row.cover_image_url,
        "cover_image_alt_en": row.cover_image_alt_en,
        "cover_image_alt_kha": row.cover_image_alt_kha,
        "featured": bool(row.featured),
        "pinned": bool(row.pinned),
        "created_at": row.created_at,
        "updated_at": row.updated_at,
        "published_at": row.published_at,
        "scheduled_at": row.scheduled_at,
    }


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


def _apply_payload(row: CMSPublication, payload: PublicationIn, db: Session) -> None:
    if payload.content_type not in CONTENT_TYPES:
        raise HTTPException(status_code=400, detail="invalid_content_type")
    if payload.kind == "page":
        content_type = "page"
    else:
        if payload.content_type not in POST_CONTENT_TYPES:
            raise HTTPException(status_code=400, detail="invalid_post_content_type")
        content_type = payload.content_type

    title_en = _clean_text(payload.title_en, 240)
    title_kha = _clean_text(payload.title_kha, 240)
    if not title_en and not title_kha:
        raise HTTPException(status_code=400, detail="title_required")
    if payload.language_mode == "en" and not title_en:
        raise HTTPException(status_code=400, detail="english_title_required")
    if payload.language_mode == "kha" and not title_kha:
        raise HTTPException(status_code=400, detail="khasi_title_required")

    desired_slug = payload.slug or title_en or title_kha or "content"
    row.slug = _unique_slug(db, desired_slug, row.id if row.id else None)
    row.kind = payload.kind
    row.content_type = content_type
    row.status = payload.status
    row.language_mode = payload.language_mode
    row.title_en = title_en
    row.title_kha = title_kha
    row.summary_en = _clean_text(payload.summary_en, 1200)
    row.summary_kha = _clean_text(payload.summary_kha, 1200)
    row.body_en = _clean_rich(payload.body_en)
    row.body_kha = _clean_rich(payload.body_kha)
    row.blocks_en_json = json.dumps(_safe_blocks(payload.blocks_en), ensure_ascii=False, separators=(",", ":"))
    row.blocks_kha_json = json.dumps(_safe_blocks(payload.blocks_kha), ensure_ascii=False, separators=(",", ":"))
    row.cover_image_url = _safe_url(payload.cover_image_url, image=True) if payload.cover_image_url else None
    row.cover_image_alt_en = _clean_text(payload.cover_image_alt_en, 500)
    row.cover_image_alt_kha = _clean_text(payload.cover_image_alt_kha, 500)
    row.featured = bool(payload.featured) if payload.kind == "post" else False
    row.pinned = bool(payload.pinned) if payload.kind == "post" else False
    row.scheduled_at = payload.scheduled_at
    row.updated_at = _now()

    if row.status == "scheduled" and row.scheduled_at is None:
        raise HTTPException(status_code=400, detail="scheduled_time_required")
    if row.status == "published" and row.published_at is None:
        row.published_at = _now()


@router.get("/api/content/posts")
def public_posts(
    response: Response,
    language: str = Query(default="en", pattern="^(en|kha)$"),
    content_type: str | None = Query(default=None, max_length=40),
    featured: bool | None = None,
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0, le=5000),
    db: Session = Depends(get_db),
):
    response.headers["Cache-Control"] = "no-store, max-age=0"
    query = db.query(CMSPublication).filter(CMSPublication.kind == "post", _visible_filter())
    if content_type:
        query = query.filter(CMSPublication.content_type == content_type)
    if featured is not None:
        query = query.filter(CMSPublication.featured.is_(featured))
    total = query.with_entities(func.count(CMSPublication.id)).scalar() or 0
    rows = (
        query.order_by(
            CMSPublication.pinned.desc(),
            CMSPublication.published_at.desc(),
            CMSPublication.scheduled_at.desc(),
            CMSPublication.created_at.desc(),
        )
        .offset(offset)
        .limit(limit)
        .all()
    )
    return {"items": [_localized(row, language) for row in rows], "total": total, "limit": limit, "offset": offset}


@router.get("/api/content/posts/{slug}")
def public_post(slug: str, response: Response, language: str = Query(default="en", pattern="^(en|kha)$"), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store, max-age=0"
    row = (
        db.query(CMSPublication)
        .filter(CMSPublication.kind == "post", CMSPublication.slug == slug, _visible_filter())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="post_not_found")
    return _localized(row, language)


@router.get("/api/content/pages/{slug}")
def public_page(slug: str, response: Response, language: str = Query(default="en", pattern="^(en|kha)$"), db: Session = Depends(get_db)):
    response.headers["Cache-Control"] = "no-store, max-age=0"
    row = (
        db.query(CMSPublication)
        .filter(CMSPublication.kind == "page", CMSPublication.slug == slug, _visible_filter())
        .first()
    )
    if not row:
        raise HTTPException(status_code=404, detail="page_not_found")
    return _localized(row, language)


@router.get("/api/admin/publications")
def admin_publications(
    kind: str | None = Query(default=None, pattern="^(post|page)$"),
    status: str | None = Query(default=None, pattern="^(draft|published|scheduled|archived)$"),
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    query = db.query(CMSPublication)
    if kind:
        query = query.filter(CMSPublication.kind == kind)
    if status:
        query = query.filter(CMSPublication.status == status)
    rows = query.order_by(CMSPublication.updated_at.desc()).limit(500).all()
    counts = dict(db.query(CMSPublication.status, func.count(CMSPublication.id)).group_by(CMSPublication.status).all())
    return {"items": [_admin_publication(row) for row in rows], "counts": {k: int(counts.get(k, 0)) for k in STATUSES}}


@router.get("/api/admin/publications/{publication_id}")
def admin_publication(publication_id: int, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    row = db.get(CMSPublication, publication_id)
    if not row:
        raise HTTPException(status_code=404, detail="publication_not_found")
    return _admin_publication(row)


@router.post("/api/admin/publications", status_code=201)
def admin_create_publication(
    payload: PublicationIn,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    row = CMSPublication(slug=f"pending-{uuid.uuid4().hex}")
    _apply_payload(row, payload, db)
    db.add(row)
    db.commit()
    db.refresh(row)
    return _admin_publication(row)


@router.put("/api/admin/publications/{publication_id}")
def admin_update_publication(
    publication_id: int,
    payload: PublicationIn,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    row = db.get(CMSPublication, publication_id)
    if not row:
        raise HTTPException(status_code=404, detail="publication_not_found")
    _apply_payload(row, payload, db)
    db.commit()
    db.refresh(row)
    return _admin_publication(row)


@router.post("/api/admin/publications/{publication_id}/duplicate", status_code=201)
def admin_duplicate_publication(
    publication_id: int,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    source = db.get(CMSPublication, publication_id)
    if not source:
        raise HTTPException(status_code=404, detail="publication_not_found")
    row = CMSPublication(
        kind=source.kind,
        content_type=source.content_type,
        slug=_unique_slug(db, f"{source.slug}-copy"),
        status="draft",
        language_mode=source.language_mode,
        title_en=(f"{source.title_en} (Copy)" if source.title_en else None),
        title_kha=(f"{source.title_kha} (Copy)" if source.title_kha else None),
        summary_en=source.summary_en,
        summary_kha=source.summary_kha,
        body_en=source.body_en,
        body_kha=source.body_kha,
        blocks_en_json=source.blocks_en_json,
        blocks_kha_json=source.blocks_kha_json,
        cover_image_url=source.cover_image_url,
        cover_image_alt_en=source.cover_image_alt_en,
        cover_image_alt_kha=source.cover_image_alt_kha,
        featured=False,
        pinned=False,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return _admin_publication(row)


@router.delete("/api/admin/publications/{publication_id}")
def admin_archive_publication(
    publication_id: int,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    row = db.get(CMSPublication, publication_id)
    if not row:
        raise HTTPException(status_code=404, detail="publication_not_found")
    row.status = "archived"
    row.updated_at = _now()
    db.commit()
    return {"archived": True, "id": row.id}


@router.get("/api/admin/media")
def admin_media(session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(CMSMedia).order_by(CMSMedia.created_at.desc()).limit(500).all()
    return {
        "items": [
            {
                "id": row.id,
                "url": row.url,
                "object_name": row.object_name,
                "filename": row.filename,
                "content_type": row.content_type,
                "size_bytes": row.size_bytes,
                "created_at": row.created_at,
            }
            for row in rows
        ]
    }


@router.post("/api/admin/media/upload", status_code=201)
async def admin_media_upload(
    request: Request,
    file: UploadFile = File(...),
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    bucket_name = os.getenv("CMS_BUCKET", "").strip()
    if not bucket_name:
        raise HTTPException(status_code=503, detail="cms_bucket_not_configured")

    allowed = {
        "image/jpeg": "jpg",
        "image/png": "png",
        "image/webp": "webp",
        "image/gif": "gif",
    }
    content_type = (file.content_type or "").lower()
    extension = allowed.get(content_type)
    if not extension:
        raise HTTPException(status_code=415, detail="unsupported_image_type")

    data = await file.read(10 * 1024 * 1024 + 1)
    if len(data) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="image_too_large")
    if not data:
        raise HTTPException(status_code=400, detail="empty_image")

    object_name = f"cms/{datetime.now(timezone.utc):%Y/%m}/{uuid.uuid4().hex}.{extension}"
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.cache_control = "public, max-age=3600"
        blob.upload_from_string(data, content_type=content_type)
        blob.patch()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="image_upload_failed") from exc

    url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
    row = CMSMedia(
        object_name=object_name,
        url=url,
        filename=(file.filename or f"image.{extension}")[:255],
        content_type=content_type,
        size_bytes=len(data),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "url": row.url,
        "object_name": row.object_name,
        "filename": row.filename,
        "content_type": row.content_type,
        "size_bytes": row.size_bytes,
        "created_at": row.created_at,
    }
