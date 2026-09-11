from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, UniqueConstraint
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
