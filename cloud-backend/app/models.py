from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


def utcnow():
    return datetime.now(timezone.utc)


class PrayerIntention(Base):
    __tablename__ = "prayer_intentions"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    intention: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(80))
    email: Mapped[str] = mapped_column(String(254))
    subject: Mapped[str] = mapped_column(String(160))
    message: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class SaveOneSoulParticipant(Base):
    """Anonymous 7-day campaign progress.

    The browser keeps a random token. Only its SHA-256 hash is stored here.
    No name, email, phone number, IP address, or prayer subject is stored.
    """

    __tablename__ = "save_one_soul_participants"
    id: Mapped[int] = mapped_column(primary_key=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    day1: Mapped[bool] = mapped_column(Boolean, default=False)
    day2: Mapped[bool] = mapped_column(Boolean, default=False)
    day3: Mapped[bool] = mapped_column(Boolean, default=False)
    day4: Mapped[bool] = mapped_column(Boolean, default=False)
    day5: Mapped[bool] = mapped_column(Boolean, default=False)
    day6: Mapped[bool] = mapped_column(Boolean, default=False)
    day7: Mapped[bool] = mapped_column(Boolean, default=False)


class CMSOverride(Base):
    """One editorial override applied to an existing public-page DOM element.

    The static GitHub Pages HTML remains the canonical technical shell. The CMS
    stores only approved editorial fields (text/HTML, link href, image src/alt)
    against deterministic CSS selectors. Interactive widgets and other elements
    carrying data-* attributes are excluded from the editor.
    """

    __tablename__ = "cms_overrides"
    __table_args__ = (
        UniqueConstraint("page_path", "selector", "field", name="uq_cms_page_selector_field"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    page_path: Mapped[str] = mapped_column(String(240), index=True)
    selector: Mapped[str] = mapped_column(String(700))
    field: Mapped[str] = mapped_column(String(16))
    value: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class CMSPublication(Base):
    """Editorial content created through the Mercy Admin publishing composer.

    kind='post' is used for feed-style content such as reflections, prayers,
    announcements and events. kind='page' is used for permanent CMS-created
    pages assembled from safe structured blocks.
    """

    __tablename__ = "cms_publications"

    id: Mapped[int] = mapped_column(primary_key=True)
    kind: Mapped[str] = mapped_column(String(16), default="post", index=True)
    content_type: Mapped[str] = mapped_column(String(40), default="reflection", index=True)
    slug: Mapped[str] = mapped_column(String(180), unique=True, index=True)
    status: Mapped[str] = mapped_column(String(16), default="draft", index=True)
    language_mode: Mapped[str] = mapped_column(String(8), default="en")

    title_en: Mapped[str | None] = mapped_column(String(240), nullable=True)
    title_kha: Mapped[str | None] = mapped_column(String(240), nullable=True)
    summary_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_kha: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_en: Mapped[str | None] = mapped_column(Text, nullable=True)
    body_kha: Mapped[str | None] = mapped_column(Text, nullable=True)
    blocks_en_json: Mapped[str] = mapped_column(Text, default="[]")
    blocks_kha_json: Mapped[str] = mapped_column(Text, default="[]")

    cover_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_image_alt_en: Mapped[str | None] = mapped_column(String(500), nullable=True)
    cover_image_alt_kha: Mapped[str | None] = mapped_column(String(500), nullable=True)

    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scheduled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class CMSMedia(Base):
    """Metadata for public website assets uploaded through Mercy Admin."""

    __tablename__ = "cms_media"

    id: Mapped[int] = mapped_column(primary_key=True)
    object_name: Mapped[str] = mapped_column(String(500), unique=True, index=True)
    url: Mapped[str] = mapped_column(Text)
    filename: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(100))
    size_bytes: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class CourseVideo(Base):
    """Video assigned to a Codex/formation course without hard-coding page HTML."""

    __tablename__ = "course_videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    course_key: Mapped[str] = mapped_column(String(80), index=True)
    topic: Mapped[str | None] = mapped_column(String(180), nullable=True, index=True)
    lesson: Mapped[str | None] = mapped_column(String(180), nullable=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    speaker: Mapped[str | None] = mapped_column(String(180), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(180), nullable=True)
    source_type: Mapped[str] = mapped_column(String(24), default="youtube")
    video_url: Mapped[str] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="en")
    doctrinal_classification: Mapped[str | None] = mapped_column(String(80), nullable=True)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    published: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class HomileticVideo(Base):
    """Preaching and homiletic media kept separate from formal course material."""

    __tablename__ = "homiletic_videos"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(240))
    speaker: Mapped[str | None] = mapped_column(String(180), nullable=True)
    occasion: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    liturgical_season: Mapped[str | None] = mapped_column(String(80), nullable=True, index=True)
    liturgical_cycle: Mapped[str | None] = mapped_column(String(16), nullable=True)
    scripture_reference: Mapped[str | None] = mapped_column(String(240), nullable=True)
    theme: Mapped[str | None] = mapped_column(String(180), nullable=True)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    body: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_type: Mapped[str] = mapped_column(String(24), default="youtube")
    video_url: Mapped[str] = mapped_column(Text)
    audio_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="en")
    featured: Mapped[bool] = mapped_column(Boolean, default=False)
    published: Mapped[bool] = mapped_column(Boolean, default=True, index=True)
    preached_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class LiveBroadcast(Base):
    """Metadata and YouTube binding for a Save One Soul live event."""

    __tablename__ = "live_broadcasts"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(240))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    category: Mapped[str] = mapped_column(String(80), default="special-event", index=True)
    speaker: Mapped[str | None] = mapped_column(String(180), nullable=True)
    scripture_reference: Mapped[str | None] = mapped_column(String(240), nullable=True)
    language: Mapped[str] = mapped_column(String(16), default="en")
    scheduled_start: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True, index=True)
    status: Mapped[str] = mapped_column(String(24), default="scheduled", index=True)
    visibility: Mapped[str] = mapped_column(String(16), default="public")
    youtube_broadcast_id: Mapped[str | None] = mapped_column(String(120), nullable=True, index=True)
    youtube_stream_id: Mapped[str | None] = mapped_column(String(120), nullable=True)
    youtube_video_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    stream_key: Mapped[str | None] = mapped_column(Text, nullable=True)
    ingestion_address: Mapped[str | None] = mapped_column(Text, nullable=True)
    thumbnail_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    show_on_homepage: Mapped[bool] = mapped_column(Boolean, default=True)
    archive_destination: Mapped[str | None] = mapped_column(String(80), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
