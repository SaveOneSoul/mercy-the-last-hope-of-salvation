import base64
import hashlib
import hmac
import json
import os
import secrets
import time
import uuid
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import bleach
import httpx
from bs4 import BeautifulSoup, Tag
from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from google.cloud import storage
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .db import get_db
from .models import CMSOverride, SaveOneSoulParticipant

router = APIRouter()

ADMIN_COOKIE = "mercy_admin_session"
ADMIN_SESSION_SECONDS = 8 * 60 * 60
PUBLIC_SITE_BASE = os.getenv(
    "PUBLIC_SITE_BASE",
    "https://saveonesoul.github.io/mercy-the-last-hope-of-salvation",
).rstrip("/")
REPO_PREFIX = "/mercy-the-last-hope-of-salvation"

EDITABLE_PAGES = [
    ("/index.html", "Home"),
    ("/pages/about.html", "About Rivaldo Kurbah"),
    ("/pages/save-one-soul.html", "Save One Soul"),
    ("/pages/pro-life.html", "Pro-Life"),
    ("/pages/saints.html", "Saints"),
    ("/pages/rosary.html", "Rosary"),
    ("/pages/prayer.html", "Prayer"),
    ("/pages/marian-prayers.html", "Marian Prayer Library"),
    ("/pages/seven-sorrows.html", "Seven Sorrows"),
    ("/pages/divine-mercy-chaplet.html", "Divine Mercy Chaplet"),
    ("/pages/precious-blood.html", "Precious Blood"),
    ("/pages/eucharistic-miracles.html", "Eucharistic Miracles"),
    ("/pages/charis.html", "CHARIS"),
    ("/pages/catholic-ai.html", "Catholic AI"),
    ("/pages/sources.html", "Sources & Editorial Policy"),
    ("/kh/index.html", "Khasi Home"),
    ("/kh/pages/save-one-soul.html", "Khasi Save One Soul"),
    ("/kh/pages/pro-life.html", "Khasi Pro-Life"),
    ("/kh/pages/saints.html", "Khasi Saints"),
    ("/kh/pages/rosary.html", "Khasi Rosary"),
    ("/kh/pages/prayer.html", "Khasi Prayer"),
    ("/kh/pages/marian-prayers.html", "Khasi Marian Prayer Library"),
    ("/kh/pages/seven-sorrows.html", "Khasi Seven Sorrows"),
    ("/kh/pages/divine-mercy-chaplet.html", "Khasi Divine Mercy Chaplet"),
    ("/kh/pages/precious-blood.html", "Khasi Precious Blood"),
    ("/kh/pages/eucharistic-miracles.html", "Khasi Eucharistic Miracles"),
    ("/kh/pages/charis.html", "Khasi CHARIS"),
    ("/kh/pages/catholic-ai.html", "Khasi Catholic AI"),
    ("/kh/pages/sources.html", "Khasi Sources"),
]
EDITABLE_PATHS = {path for path, _ in EDITABLE_PAGES}
PAGE_TITLES = dict(EDITABLE_PAGES)

TEXT_TAGS = {"h1", "h2", "h3", "h4", "p", "li", "blockquote", "figcaption"}
LOCKED_TAGS = {"form", "button", "input", "textarea", "select", "option", "script", "style", "iframe"}
ALLOWED_HTML_TAGS = [
    "a", "abbr", "b", "br", "cite", "code", "em", "i", "mark", "q",
    "small", "span", "strong", "sub", "sup", "u",
]
ALLOWED_HTML_ATTRIBUTES = {
    "a": ["href", "target", "rel", "title"],
    "abbr": ["title"],
    "span": ["class"],
}
ALLOWED_PROTOCOLS = ["http", "https", "mailto", "tel"]

_login_attempts: dict[str, list[float]] = defaultdict(list)


class AdminLoginIn(BaseModel):
    password: str = Field(min_length=8, max_length=256)


class ContentEdit(BaseModel):
    selector: str = Field(min_length=1, max_length=700)
    field: str = Field(pattern="^(html|href|src|alt)$")
    value: str = Field(max_length=30000)


class ContentBatchIn(BaseModel):
    page_path: str = Field(min_length=1, max_length=240)
    edits: list[ContentEdit] = Field(max_length=500)


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _unb64(value: str) -> bytes:
    return base64.urlsafe_b64decode(value + "=" * (-len(value) % 4))


def _admin_password() -> str:
    return os.getenv("ADMIN_PASSWORD", "")


def _session_secret() -> bytes:
    value = os.getenv("ADMIN_SESSION_SECRET", "")
    if not value:
        return b""
    return value.encode("utf-8")


def _admin_enabled() -> bool:
    return bool(_admin_password() and _session_secret())


def _client_key(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for", "")
    if forwarded:
        return forwarded.split(",")[0].strip() or "unknown"
    return request.client.host if request.client else "unknown"


def _rate_limit_login(request: Request) -> None:
    now = time.time()
    key = _client_key(request)
    recent = [t for t in _login_attempts[key] if now - t < 15 * 60]
    _login_attempts[key] = recent
    if len(recent) >= 10:
        raise HTTPException(status_code=429, detail="too_many_login_attempts")
    recent.append(now)


def _make_session() -> tuple[str, str]:
    csrf = secrets.token_urlsafe(24)
    payload = {
        "exp": int(time.time()) + ADMIN_SESSION_SECONDS,
        "csrf": csrf,
    }
    encoded = _b64(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    signature = _b64(hmac.new(_session_secret(), encoded.encode("ascii"), hashlib.sha256).digest())
    return f"{encoded}.{signature}", csrf


def _read_session(request: Request) -> dict:
    if not _admin_enabled():
        raise HTTPException(status_code=503, detail="admin_not_configured")
    token = request.cookies.get(ADMIN_COOKIE, "")
    try:
        encoded, signature = token.split(".", 1)
        expected = _b64(hmac.new(_session_secret(), encoded.encode("ascii"), hashlib.sha256).digest())
        if not hmac.compare_digest(signature, expected):
            raise ValueError("bad signature")
        payload = json.loads(_unb64(encoded).decode("utf-8"))
        if int(payload.get("exp", 0)) <= int(time.time()):
            raise ValueError("expired")
        if not payload.get("csrf"):
            raise ValueError("missing csrf")
        return payload
    except Exception as exc:
        raise HTTPException(status_code=401, detail="admin_auth_required") from exc


def require_admin(request: Request) -> dict:
    return _read_session(request)


def _require_write_guard(request: Request, session: dict) -> None:
    csrf = request.headers.get("x-csrf-token", "")
    if not csrf or not hmac.compare_digest(csrf, str(session.get("csrf", ""))):
        raise HTTPException(status_code=403, detail="csrf_failed")
    origin = request.headers.get("origin", "")
    if origin:
        expected = f"{request.url.scheme}://{request.url.netloc}"
        if origin.rstrip("/") != expected.rstrip("/"):
            raise HTTPException(status_code=403, detail="origin_failed")


def normalize_page_path(value: str) -> str:
    raw = (value or "").strip().split("?", 1)[0].split("#", 1)[0]
    if raw.startswith("http://") or raw.startswith("https://"):
        raw = urlparse(raw).path
    if raw.startswith(REPO_PREFIX):
        raw = raw[len(REPO_PREFIX):] or "/"
    if not raw.startswith("/"):
        raw = "/" + raw
    if raw == "/":
        raw = "/index.html"
    elif raw.endswith("/"):
        raw += "index.html"
    return raw


def validate_page_path(value: str) -> str:
    path = normalize_page_path(value)
    if path not in EDITABLE_PATHS:
        raise HTTPException(status_code=400, detail="page_not_editable")
    return path


def _has_data_attribute(tag: Tag) -> bool:
    return any(str(name).lower().startswith("data-") for name in tag.attrs.keys())


def _is_locked(tag: Tag, main: Tag) -> bool:
    current = tag
    while isinstance(current, Tag):
        if current.name in LOCKED_TAGS or _has_data_attribute(current):
            return True
        if current is main:
            break
        current = current.parent
    return False


def _nth_of_type(tag: Tag) -> int:
    if not isinstance(tag.parent, Tag):
        return 1
    same = [child for child in tag.parent.children if isinstance(child, Tag) and child.name == tag.name]
    try:
        return same.index(tag) + 1
    except ValueError:
        return 1


def _selector(tag: Tag, main: Tag) -> str:
    parts: list[str] = []
    current = tag
    while isinstance(current, Tag) and current is not main:
        parts.append(f"{current.name}:nth-of-type({_nth_of_type(current)})")
        current = current.parent
    parts.reverse()
    return "main > " + " > ".join(parts)


def _text_candidate(tag: Tag) -> bool:
    if tag.name in TEXT_TAGS:
        return True
    classes = set(tag.get("class", []))
    if tag.name == "div" and ("crumb" in classes or "callout" in classes):
        nested = tag.find(TEXT_TAGS)
        return nested is None
    return False


def _sanitize_html(value: str) -> str:
    return bleach.clean(
        value,
        tags=ALLOWED_HTML_TAGS,
        attributes=ALLOWED_HTML_ATTRIBUTES,
        protocols=ALLOWED_PROTOCOLS,
        strip=True,
    )


def _safe_resource_value(field: str, value: str) -> str:
    value = value.strip()
    if field == "alt":
        return value[:1000]
    if not value:
        return ""
    if value.startswith(("/", "./", "../", "#")):
        return value
    parsed = urlparse(value)
    if field == "src":
        if parsed.scheme != "https":
            raise HTTPException(status_code=400, detail="image_url_must_use_https")
    elif parsed.scheme not in {"http", "https", "mailto", "tel"}:
        raise HTTPException(status_code=400, detail="unsupported_link_scheme")
    return value


def _serialize_override(row: CMSOverride) -> dict:
    return {
        "selector": row.selector,
        "field": row.field,
        "value": row.value,
        "updated_at": row.updated_at,
    }


@router.get("/admin", include_in_schema=False)
def admin_page():
    path = Path(__file__).resolve().parent / "static" / "admin.html"
    response = FileResponse(path, media_type="text/html")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.post("/api/admin/login")
def admin_login(payload: AdminLoginIn, request: Request, response: Response):
    if not _admin_enabled():
        raise HTTPException(status_code=503, detail="admin_not_configured")
    _rate_limit_login(request)
    if not hmac.compare_digest(payload.password.encode("utf-8"), _admin_password().encode("utf-8")):
        time.sleep(0.35)
        raise HTTPException(status_code=401, detail="invalid_admin_password")
    token, csrf = _make_session()
    response.set_cookie(
        ADMIN_COOKIE,
        token,
        max_age=ADMIN_SESSION_SECONDS,
        secure=True,
        httponly=True,
        samesite="strict",
        path="/",
    )
    return {"authenticated": True, "csrf": csrf, "expires_in": ADMIN_SESSION_SECONDS}


@router.post("/api/admin/logout")
def admin_logout(request: Request, response: Response, session: dict = Depends(require_admin)):
    _require_write_guard(request, session)
    response.delete_cookie(ADMIN_COOKIE, path="/")
    return {"authenticated": False}


@router.get("/api/admin/me")
def admin_me(session: dict = Depends(require_admin)):
    return {"authenticated": True, "csrf": session["csrf"], "expires_at": session["exp"]}


@router.get("/api/admin/dashboard")
def admin_dashboard(
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    joined = db.query(func.count(SaveOneSoulParticipant.id)).scalar() or 0
    completed = (
        db.query(func.count(SaveOneSoulParticipant.id))
        .filter(SaveOneSoulParticipant.completed_at.isnot(None))
        .scalar()
        or 0
    )
    english = (
        db.query(func.count(SaveOneSoulParticipant.id))
        .filter(SaveOneSoulParticipant.language == "en")
        .scalar()
        or 0
    )
    khasi = (
        db.query(func.count(SaveOneSoulParticipant.id))
        .filter(SaveOneSoulParticipant.language == "kha")
        .scalar()
        or 0
    )
    day_counts = {}
    for day in range(1, 8):
        day_counts[str(day)] = (
            db.query(func.count(SaveOneSoulParticipant.id))
            .filter(getattr(SaveOneSoulParticipant, f"day{day}").is_(True))
            .scalar()
            or 0
        )

    rows = (
        db.query(SaveOneSoulParticipant)
        .order_by(SaveOneSoulParticipant.started_at.desc())
        .limit(250)
        .all()
    )
    participants = []
    for row in rows:
        days = [bool(getattr(row, f"day{i}")) for i in range(1, 8)]
        participants.append(
            {
                "anonymous_id": row.token_hash[:12],
                "language": row.language,
                "started_at": row.started_at,
                "completed_at": row.completed_at,
                "days": days,
                "days_completed": sum(days),
                "completed": row.completed_at is not None,
            }
        )

    return {
        "joined": joined,
        "completed": completed,
        "in_progress": max(joined - completed, 0),
        "english": english,
        "khasi": khasi,
        "day_completions": day_counts,
        "participants": participants,
        "privacy": "anonymous_records_only",
    }


@router.get("/api/admin/pages")
def admin_pages(session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    counts = dict(
        db.query(CMSOverride.page_path, func.count(CMSOverride.id))
        .group_by(CMSOverride.page_path)
        .all()
    )
    return {
        "pages": [
            {"path": path, "title": title, "overrides": int(counts.get(path, 0))}
            for path, title in EDITABLE_PAGES
        ]
    }


@router.get("/api/content/blocks")
def public_content_blocks(path: str, response: Response, db: Session = Depends(get_db)):
    page_path = normalize_page_path(path)
    response.headers["Cache-Control"] = "no-store, max-age=0"
    if page_path not in EDITABLE_PATHS:
        return {"page_path": page_path, "overrides": []}
    rows = (
        db.query(CMSOverride)
        .filter(CMSOverride.page_path == page_path)
        .order_by(CMSOverride.selector.asc(), CMSOverride.field.asc())
        .all()
    )
    return {"page_path": page_path, "overrides": [_serialize_override(row) for row in rows]}


@router.get("/api/admin/page-fields")
async def admin_page_fields(
    path: str,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    page_path = validate_page_path(path)
    url = PUBLIC_SITE_BASE + page_path
    try:
        async with httpx.AsyncClient(timeout=15, follow_redirects=True) as client:
            result = await client.get(url, headers={"Cache-Control": "no-cache"})
            result.raise_for_status()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="could_not_load_live_page") from exc

    soup = BeautifulSoup(result.text, "html.parser")
    main = soup.find("main")
    if not isinstance(main, Tag):
        raise HTTPException(status_code=422, detail="page_has_no_main")

    override_rows = db.query(CMSOverride).filter(CMSOverride.page_path == page_path).all()
    overrides = {(row.selector, row.field): row.value for row in override_rows}

    blocks = []
    seen = set()
    for tag in main.find_all(True):
        if _is_locked(tag, main):
            continue
        selector = _selector(tag, main)
        if not selector or selector in seen:
            continue

        if tag.name == "img":
            seen.add(selector)
            blocks.append(
                {
                    "kind": "image",
                    "tag": "img",
                    "selector": selector,
                    "src": overrides.get((selector, "src"), tag.get("src", "")),
                    "alt": overrides.get((selector, "alt"), tag.get("alt", "")),
                    "overridden": any((selector, f) in overrides for f in ("src", "alt")),
                }
            )
            continue

        if tag.name == "a" and tag.has_attr("href"):
            seen.add(selector)
            blocks.append(
                {
                    "kind": "link",
                    "tag": "a",
                    "selector": selector,
                    "html": overrides.get((selector, "html"), tag.decode_contents()),
                    "href": overrides.get((selector, "href"), tag.get("href", "")),
                    "overridden": any((selector, f) in overrides for f in ("html", "href")),
                }
            )
            continue

        if _text_candidate(tag):
            seen.add(selector)
            text = " ".join(tag.stripped_strings)
            if not text:
                continue
            blocks.append(
                {
                    "kind": "text",
                    "tag": tag.name,
                    "selector": selector,
                    "html": overrides.get((selector, "html"), tag.decode_contents()),
                    "preview": text[:140],
                    "overridden": (selector, "html") in overrides,
                }
            )

    return {
        "page_path": page_path,
        "title": PAGE_TITLES.get(page_path, page_path),
        "source_url": url,
        "blocks": blocks,
        "technical_policy": "elements inside data-* widgets and form controls are locked and excluded",
    }


@router.put("/api/admin/content/batch")
def admin_save_content(
    payload: ContentBatchIn,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    page_path = validate_page_path(payload.page_path)
    saved = 0
    for edit in payload.edits:
        field = edit.field
        value = edit.value
        if field == "html":
            value = _sanitize_html(value)
        else:
            value = _safe_resource_value(field, value)

        row = (
            db.query(CMSOverride)
            .filter_by(page_path=page_path, selector=edit.selector, field=field)
            .first()
        )
        if row:
            row.value = value
            row.updated_at = datetime.now(timezone.utc)
        else:
            db.add(
                CMSOverride(
                    page_path=page_path,
                    selector=edit.selector,
                    field=field,
                    value=value,
                )
            )
        saved += 1
    db.commit()
    return {"saved": saved, "page_path": page_path}


@router.delete("/api/admin/content/page")
def admin_reset_page(
    path: str,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    page_path = validate_page_path(path)
    deleted = db.query(CMSOverride).filter(CMSOverride.page_path == page_path).delete()
    db.commit()
    return {"deleted": deleted, "page_path": page_path}


@router.post("/api/admin/upload-image")
async def admin_upload_image(
    request: Request,
    file: UploadFile = File(...),
    session: dict = Depends(require_admin),
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

    data = await file.read(5 * 1024 * 1024 + 1)
    if len(data) > 5 * 1024 * 1024:
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

    return {
        "url": f"https://storage.googleapis.com/{bucket_name}/{object_name}",
        "object": object_name,
        "content_type": content_type,
    }
