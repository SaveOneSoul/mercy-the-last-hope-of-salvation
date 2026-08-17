from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import create_engine, String, Text, DateTime, Integer
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker
from .settings import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, pool_pre_ping=True, connect_args=connect_args)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


class Base(DeclarativeBase):
    pass


class ContactMessage(Base):
    __tablename__ = "contact_messages"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    name: Mapped[str] = mapped_column(String(100))
    email: Mapped[str | None] = mapped_column(String(200), nullable=True)
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    topic: Mapped[str] = mapped_column(String(100))
    message: Mapped[str] = mapped_column(Text)
    automatic_reply: Mapped[str | None] = mapped_column(Text, nullable=True)


def init_db() -> None:
    if settings.persist_contact_messages:
        Base.metadata.create_all(bind=engine)


def save_contact_message(*, name: str, email: str | None, phone: str | None, topic: str, message: str, automatic_reply: str) -> bool:
    if not settings.persist_contact_messages:
        return False
    with SessionLocal() as db:
        row = ContactMessage(
            name=name,
            email=email,
            phone=phone,
            topic=topic,
            message=message,
            automatic_reply=automatic_reply,
        )
        db.add(row)
        db.commit()
    return True
