import os
import re
import uuid
from datetime import datetime, timezone
from urllib.parse import urlparse, parse_qs

import httpx
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from google.cloud import storage
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from .cms_admin import _require_write_guard, require_admin
from .db import get_db
from .models import CourseVideo, HomileticVideo, LiveBroadcast, CMSMedia

router = APIRouter()

COURSES = {
    "theology", "philosophy", "logos", "pneumatology", "charismatic-renewal",
    "angelology-demonology", "patristics", "church-fathers", "magisterium",
    "canon-law", "spiritual-theology", "apologetics", "mariology",
    "church-history", "formation"
}
SOURCE_TYPES = {"youtube", "uploaded", "external"}
LIVE_STATUSES = {"scheduled", "ready", "live", "completed", "cancelled"}


def _now():
    return datetime.now(timezone.utc)


def _clean(value: str | None, limit: int = 3000) -> str | None:
    if value is None:
        return None
    value = value.strip()
    return value[:limit] if value else None


def _safe_https(value: str | None, *, allow_youtube_id: bool = False) -> str | None:
    value = _clean(value)
    if value is None:
        return None
    if allow_youtube_id and re.fullmatch(r"[A-Za-z0-9_-]{6,120}", value):
        return value
    parsed = urlparse(value)
    if parsed.scheme != "https":
        raise HTTPException(status_code=400, detail="https_url_required")
    return value


def _youtube_id(value: str | None) -> str | None:
    value = _clean(value)
    if not value:
        return None
    if re.fullmatch(r"[A-Za-z0-9_-]{6,120}", value):
        return value
    try:
        parsed = urlparse(value)
        host = parsed.netloc.lower()
        if host.endswith("youtu.be"):
            return parsed.path.strip("/").split("/")[0] or None
        if "youtube.com" in host:
            if parsed.path == "/watch":
                return (parse_qs(parsed.query).get("v") or [None])[0]
            if parsed.path.startswith("/live/") or parsed.path.startswith("/embed/"):
                parts = parsed.path.strip("/").split("/")
                return parts[1] if len(parts) > 1 else None
    except Exception:
        return None
    return None


class CourseVideoIn(BaseModel):
    course_key: str = Field(max_length=80)
    topic: str | None = Field(default=None, max_length=180)
    lesson: str | None = Field(default=None, max_length=180)
    title: str = Field(min_length=2, max_length=240)
    description: str | None = Field(default=None, max_length=5000)
    speaker: str | None = Field(default=None, max_length=180)
    source_name: str | None = Field(default=None, max_length=180)
    source_type: str = Field(default="youtube", pattern="^(youtube|uploaded|external)$")
    video_url: str = Field(min_length=2, max_length=3000)
    thumbnail_url: str | None = Field(default=None, max_length=3000)
    language: str = Field(default="en", max_length=16)
    doctrinal_classification: str | None = Field(default=None, max_length=80)
    sort_order: int = 0
    featured: bool = False
    published: bool = True


class HomileticIn(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    speaker: str | None = Field(default=None, max_length=180)
    occasion: str | None = Field(default=None, max_length=100)
    liturgical_season: str | None = Field(default=None, max_length=80)
    liturgical_cycle: str | None = Field(default=None, max_length=16)
    scripture_reference: str | None = Field(default=None, max_length=240)
    theme: str | None = Field(default=None, max_length=180)
    summary: str | None = Field(default=None, max_length=5000)
    body: str | None = Field(default=None, max_length=40000)
    source_type: str = Field(default="youtube", pattern="^(youtube|uploaded|external)$")
    video_url: str = Field(min_length=2, max_length=3000)
    audio_url: str | None = Field(default=None, max_length=3000)
    thumbnail_url: str | None = Field(default=None, max_length=3000)
    language: str = Field(default="en", max_length=16)
    featured: bool = False
    published: bool = True
    preached_at: datetime | None = None


class LiveIn(BaseModel):
    title: str = Field(min_length=2, max_length=240)
    description: str | None = Field(default=None, max_length=5000)
    category: str = Field(default="special-event", max_length=80)
    speaker: str | None = Field(default=None, max_length=180)
    scripture_reference: str | None = Field(default=None, max_length=240)
    language: str = Field(default="en", max_length=16)
    scheduled_start: datetime | None = None
    visibility: str = Field(default="public", pattern="^(public|unlisted|private)$")
    youtube_url_or_id: str | None = Field(default=None, max_length=3000)
    thumbnail_url: str | None = Field(default=None, max_length=3000)
    show_on_homepage: bool = True
    archive_destination: str | None = Field(default=None, max_length=80)
    create_on_youtube: bool = False


def _course_out(row: CourseVideo):
    return {
        "id": row.id, "course_key": row.course_key, "topic": row.topic, "lesson": row.lesson,
        "title": row.title, "description": row.description, "speaker": row.speaker,
        "source_name": row.source_name, "source_type": row.source_type, "video_url": row.video_url,
        "youtube_id": _youtube_id(row.video_url), "thumbnail_url": row.thumbnail_url,
        "language": row.language, "doctrinal_classification": row.doctrinal_classification,
        "sort_order": row.sort_order, "featured": row.featured, "published": row.published,
        "created_at": row.created_at, "updated_at": row.updated_at,
    }


def _homiletic_out(row: HomileticVideo):
    return {
        "id": row.id, "title": row.title, "speaker": row.speaker, "occasion": row.occasion,
        "liturgical_season": row.liturgical_season, "liturgical_cycle": row.liturgical_cycle,
        "scripture_reference": row.scripture_reference, "theme": row.theme, "summary": row.summary,
        "body": row.body, "source_type": row.source_type, "video_url": row.video_url,
        "youtube_id": _youtube_id(row.video_url), "audio_url": row.audio_url,
        "thumbnail_url": row.thumbnail_url, "language": row.language, "featured": row.featured,
        "published": row.published, "preached_at": row.preached_at, "created_at": row.created_at,
    }


def _live_out(row: LiveBroadcast, include_secret: bool = False):
    data = {
        "id": row.id, "title": row.title, "description": row.description, "category": row.category,
        "speaker": row.speaker, "scripture_reference": row.scripture_reference, "language": row.language,
        "scheduled_start": row.scheduled_start, "status": row.status, "visibility": row.visibility,
        "youtube_broadcast_id": row.youtube_broadcast_id, "youtube_video_url": row.youtube_video_url,
        "youtube_id": _youtube_id(row.youtube_video_url or row.youtube_broadcast_id),
        "thumbnail_url": row.thumbnail_url, "show_on_homepage": row.show_on_homepage,
        "archive_destination": row.archive_destination, "created_at": row.created_at,
    }
    if include_secret:
        data["youtube_stream_id"] = row.youtube_stream_id
        data["ingestion_address"] = row.ingestion_address
        data["stream_key"] = row.stream_key
    return data


def _youtube_configured():
    return all(os.getenv(k, "").strip() for k in (
        "YOUTUBE_CLIENT_ID", "YOUTUBE_CLIENT_SECRET", "YOUTUBE_REFRESH_TOKEN"
    ))


def _youtube_access_token() -> str:
    if not _youtube_configured():
        raise HTTPException(status_code=503, detail="youtube_oauth_not_configured")
    with httpx.Client(timeout=20) as client:
        r = client.post("https://oauth2.googleapis.com/token", data={
            "client_id": os.getenv("YOUTUBE_CLIENT_ID"),
            "client_secret": os.getenv("YOUTUBE_CLIENT_SECRET"),
            "refresh_token": os.getenv("YOUTUBE_REFRESH_TOKEN"),
            "grant_type": "refresh_token",
        })
    if r.status_code >= 400:
        raise HTTPException(status_code=502, detail="youtube_token_refresh_failed")
    token = r.json().get("access_token")
    if not token:
        raise HTTPException(status_code=502, detail="youtube_access_token_missing")
    return token


def _youtube_create(title: str, description: str | None, start: datetime | None, visibility: str):
    token = _youtube_access_token()
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    start = start or (_now())
    with httpx.Client(timeout=25) as client:
        b = client.post(
            "https://www.googleapis.com/youtube/v3/liveBroadcasts?part=snippet,status,contentDetails",
            headers=headers,
            json={
                "snippet": {
                    "title": title,
                    "description": description or "",
                    "scheduledStartTime": start.astimezone(timezone.utc).isoformat().replace("+00:00", "Z"),
                },
                "status": {"privacyStatus": visibility, "selfDeclaredMadeForKids": False},
                "contentDetails": {"enableAutoStart": True, "enableAutoStop": True},
            },
        )
        if b.status_code >= 400:
            raise HTTPException(status_code=502, detail="youtube_broadcast_create_failed")
        broadcast_id = b.json().get("id")

        s = client.post(
            "https://www.googleapis.com/youtube/v3/liveStreams?part=snippet,cdn,contentDetails,status",
            headers=headers,
            json={
                "snippet": {"title": f"{title} — Save One Soul stream"},
                "cdn": {"frameRate": "variable", "ingestionType": "rtmp", "resolution": "variable"},
            },
        )
        if s.status_code >= 400:
            raise HTTPException(status_code=502, detail="youtube_stream_create_failed")
        stream = s.json()
        stream_id = stream.get("id")
        ingestion = ((stream.get("cdn") or {}).get("ingestionInfo") or {})

        bind = client.post(
            f"https://www.googleapis.com/youtube/v3/liveBroadcasts/bind?id={broadcast_id}&part=id,contentDetails&streamId={stream_id}",
            headers=headers,
        )
        if bind.status_code >= 400:
            raise HTTPException(status_code=502, detail="youtube_broadcast_bind_failed")
    return {
        "broadcast_id": broadcast_id,
        "stream_id": stream_id,
        "ingestion_address": ingestion.get("ingestionAddress"),
        "stream_key": ingestion.get("streamName"),
        "video_url": f"https://www.youtube.com/watch?v={broadcast_id}",
    }


@router.get("/api/admin/video-studio/state")
def admin_video_studio_state(session: dict = Depends(require_admin)):
    return {
        "courses": sorted(COURSES),
        "youtube_oauth_configured": _youtube_configured(),
        "max_direct_upload_mb": 30,
    }


@router.get("/api/admin/course-videos")
def admin_course_videos(session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    return {"items": [_course_out(x) for x in db.query(CourseVideo).order_by(CourseVideo.course_key, CourseVideo.sort_order, CourseVideo.created_at.desc()).all()]}


@router.post("/api/admin/course-videos", status_code=201)
def admin_create_course_video(payload: CourseVideoIn, request: Request, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    _require_write_guard(request, session)
    key = payload.course_key.strip().lower()
    if key not in COURSES:
        raise HTTPException(status_code=400, detail="unsupported_course")
    row = CourseVideo(
        course_key=key, topic=_clean(payload.topic, 180), lesson=_clean(payload.lesson, 180),
        title=payload.title.strip(), description=_clean(payload.description, 5000),
        speaker=_clean(payload.speaker, 180), source_name=_clean(payload.source_name, 180),
        source_type=payload.source_type, video_url=_safe_https(payload.video_url) or "",
        thumbnail_url=_safe_https(payload.thumbnail_url), language=payload.language.strip().lower() or "en",
        doctrinal_classification=_clean(payload.doctrinal_classification, 80),
        sort_order=payload.sort_order, featured=payload.featured, published=payload.published,
    )
    db.add(row); db.commit(); db.refresh(row)
    return _course_out(row)


@router.delete("/api/admin/course-videos/{video_id}")
def admin_delete_course_video(video_id: int, request: Request, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    _require_write_guard(request, session)
    row = db.get(CourseVideo, video_id)
    if not row: raise HTTPException(status_code=404, detail="course_video_not_found")
    db.delete(row); db.commit()
    return {"deleted": True}


@router.get("/api/content/course-videos")
def public_course_videos(course: str = Query(max_length=80), db: Session = Depends(get_db)):
    key = course.strip().lower()
    rows = db.query(CourseVideo).filter(CourseVideo.course_key == key, CourseVideo.published.is_(True)).order_by(CourseVideo.sort_order, CourseVideo.created_at.desc()).all()
    return {"course": key, "items": [_course_out(x) for x in rows]}


@router.get("/api/admin/homiletics")
def admin_homiletics(session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    return {"items": [_homiletic_out(x) for x in db.query(HomileticVideo).order_by(HomileticVideo.created_at.desc()).all()]}


@router.post("/api/admin/homiletics", status_code=201)
def admin_create_homiletic(payload: HomileticIn, request: Request, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    _require_write_guard(request, session)
    row = HomileticVideo(
        title=payload.title.strip(), speaker=_clean(payload.speaker, 180), occasion=_clean(payload.occasion, 100),
        liturgical_season=_clean(payload.liturgical_season, 80), liturgical_cycle=_clean(payload.liturgical_cycle, 16),
        scripture_reference=_clean(payload.scripture_reference, 240), theme=_clean(payload.theme, 180),
        summary=_clean(payload.summary, 5000), body=_clean(payload.body, 40000), source_type=payload.source_type,
        video_url=_safe_https(payload.video_url) or "", audio_url=_safe_https(payload.audio_url),
        thumbnail_url=_safe_https(payload.thumbnail_url), language=payload.language.strip().lower() or "en",
        featured=payload.featured, published=payload.published, preached_at=payload.preached_at,
    )
    db.add(row); db.commit(); db.refresh(row)
    return _homiletic_out(row)


@router.delete("/api/admin/homiletics/{video_id}")
def admin_delete_homiletic(video_id: int, request: Request, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    _require_write_guard(request, session)
    row = db.get(HomileticVideo, video_id)
    if not row: raise HTTPException(status_code=404, detail="homiletic_not_found")
    db.delete(row); db.commit()
    return {"deleted": True}


@router.get("/api/content/homiletics")
def public_homiletics(db: Session = Depends(get_db)):
    rows = db.query(HomileticVideo).filter(HomileticVideo.published.is_(True)).order_by(HomileticVideo.preached_at.desc().nullslast(), HomileticVideo.created_at.desc()).limit(250).all()
    return {"items": [_homiletic_out(x) for x in rows]}


@router.post("/api/admin/media/video-upload", status_code=201)
async def admin_video_upload(request: Request, file: UploadFile = File(...), session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    _require_write_guard(request, session)
    bucket_name = os.getenv("CMS_BUCKET", "").strip()
    if not bucket_name:
        raise HTTPException(status_code=503, detail="cms_bucket_not_configured")
    allowed = {"video/mp4": "mp4", "video/webm": "webm", "video/quicktime": "mov"}
    content_type = (file.content_type or "").lower()
    ext = allowed.get(content_type)
    if not ext:
        raise HTTPException(status_code=415, detail="unsupported_video_type")
    max_bytes = 30 * 1024 * 1024
    data = await file.read(max_bytes + 1)
    if len(data) > max_bytes:
        raise HTTPException(status_code=413, detail="video_too_large_use_youtube_or_external_host")
    if not data:
        raise HTTPException(status_code=400, detail="empty_video")
    object_name = f"cms/video/{datetime.now(timezone.utc):%Y/%m}/{uuid.uuid4().hex}.{ext}"
    try:
        client = storage.Client()
        bucket = client.bucket(bucket_name)
        blob = bucket.blob(object_name)
        blob.cache_control = "public, max-age=3600"
        blob.upload_from_string(data, content_type=content_type)
        blob.patch()
    except Exception as exc:
        raise HTTPException(status_code=502, detail="video_upload_failed") from exc
    url = f"https://storage.googleapis.com/{bucket_name}/{object_name}"
    media = CMSMedia(object_name=object_name, url=url, filename=(file.filename or f"video.{ext}")[:255], content_type=content_type, size_bytes=len(data))
    db.add(media); db.commit(); db.refresh(media)
    return {"id": media.id, "url": media.url, "filename": media.filename, "content_type": media.content_type, "size_bytes": media.size_bytes}


@router.get("/api/admin/live")
def admin_live(session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    return {"youtube_oauth_configured": _youtube_configured(), "items": [_live_out(x, True) for x in db.query(LiveBroadcast).order_by(LiveBroadcast.created_at.desc()).all()]}


@router.post("/api/admin/live", status_code=201)
def admin_create_live(payload: LiveIn, request: Request, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    _require_write_guard(request, session)
    youtube = None
    if payload.create_on_youtube:
        youtube = _youtube_create(payload.title.strip(), _clean(payload.description, 5000), payload.scheduled_start, payload.visibility)
    youtube_id = _youtube_id(payload.youtube_url_or_id)
    row = LiveBroadcast(
        title=payload.title.strip(), description=_clean(payload.description, 5000),
        category=payload.category.strip().lower() or "special-event", speaker=_clean(payload.speaker, 180),
        scripture_reference=_clean(payload.scripture_reference, 240), language=payload.language.strip().lower() or "en",
        scheduled_start=payload.scheduled_start, status="ready" if youtube else "scheduled", visibility=payload.visibility,
        youtube_broadcast_id=(youtube or {}).get("broadcast_id") or youtube_id,
        youtube_stream_id=(youtube or {}).get("stream_id"),
        youtube_video_url=(youtube or {}).get("video_url") or (f"https://www.youtube.com/watch?v={youtube_id}" if youtube_id else None),
        stream_key=(youtube or {}).get("stream_key"), ingestion_address=(youtube or {}).get("ingestion_address"),
        thumbnail_url=_safe_https(payload.thumbnail_url), show_on_homepage=payload.show_on_homepage,
        archive_destination=_clean(payload.archive_destination, 80),
    )
    db.add(row); db.commit(); db.refresh(row)
    return _live_out(row, True)


class LiveStatusIn(BaseModel):
    status: str = Field(pattern="^(scheduled|ready|live|completed|cancelled)$")


@router.put("/api/admin/live/{live_id}/status")
def admin_live_status(live_id: int, payload: LiveStatusIn, request: Request, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    _require_write_guard(request, session)
    row = db.get(LiveBroadcast, live_id)
    if not row: raise HTTPException(status_code=404, detail="live_not_found")
    row.status = payload.status
    row.updated_at = _now()
    db.commit(); db.refresh(row)
    return _live_out(row, True)


@router.delete("/api/admin/live/{live_id}")
def admin_delete_live(live_id: int, request: Request, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    _require_write_guard(request, session)
    row = db.get(LiveBroadcast, live_id)
    if not row: raise HTTPException(status_code=404, detail="live_not_found")
    db.delete(row); db.commit()
    return {"deleted": True}


@router.get("/api/content/live")
def public_live(db: Session = Depends(get_db)):
    current = db.query(LiveBroadcast).filter(
        LiveBroadcast.show_on_homepage.is_(True),
        LiveBroadcast.status.in_(["live", "ready", "scheduled"])
    ).order_by(LiveBroadcast.status.desc(), LiveBroadcast.scheduled_start.asc()).first()
    recent = db.query(LiveBroadcast).filter(LiveBroadcast.status == "completed").order_by(LiveBroadcast.updated_at.desc()).limit(12).all()
    return {"current": _live_out(current) if current else None, "recent": [_live_out(x) for x in recent]}
