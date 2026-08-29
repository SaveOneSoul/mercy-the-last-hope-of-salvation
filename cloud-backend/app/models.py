from datetime import datetime, timezone
from sqlalchemy import String, Text, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from .db import Base
class PrayerIntention(Base):
    __tablename__="prayer_intentions"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str|None]=mapped_column(String(80),nullable=True)
    intention: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
class ContactMessage(Base):
    __tablename__="contact_messages"
    id: Mapped[int]=mapped_column(primary_key=True)
    name: Mapped[str]=mapped_column(String(80))
    email: Mapped[str]=mapped_column(String(254))
    subject: Mapped[str]=mapped_column(String(160))
    message: Mapped[str]=mapped_column(Text)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc))
