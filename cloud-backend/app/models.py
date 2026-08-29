from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime, Boolean
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
