import hashlib
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from .db import Base, engine, get_db
from .models import PrayerIntention, ContactMessage, SaveOneSoulParticipant

Base.metadata.create_all(bind=engine)
app = FastAPI(
    title="Mercy API",
    version="2.1.0",
    docs_url="/docs" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None,
)
origins = [x.strip() for x in os.getenv("CORS_ORIGINS", "http://localhost:5500").split(',') if x.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


class PrayerIn(BaseModel):
    name: str | None = Field(default=None, max_length=80)
    intention: str = Field(min_length=2, max_length=2000)
    website: str | None = Field(default=None, max_length=200)


class ContactIn(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    email: EmailStr
    subject: str = Field(min_length=1, max_length=160)
    message: str = Field(min_length=2, max_length=5000)
    website: str | None = Field(default=None, max_length=200)


class CampaignIn(BaseModel):
    token: str = Field(min_length=20, max_length=128)
    language: str = Field(default="en", pattern="^(en|kha)$")


class CampaignDayIn(CampaignIn):
    day: int = Field(ge=1, le=7)


def token_hash(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def get_participant(db: Session, token: str) -> SaveOneSoulParticipant:
    row = db.query(SaveOneSoulParticipant).filter_by(token_hash=token_hash(token)).first()
    if not row:
        raise HTTPException(status_code=404, detail="campaign_not_joined")
    return row


def progress_payload(row: SaveOneSoulParticipant):
    days = [bool(getattr(row, f"day{i}")) for i in range(1, 8)]
    return {
        "joined": True,
        "language": row.language,
        "days": days,
        "days_completed": sum(days),
        "completed": row.completed_at is not None,
        "started_at": row.started_at,
        "completed_at": row.completed_at,
    }


@app.get('/health')
def health():
    return {'status': 'ok', 'service': 'mercy-api', 'version': '2.1.0'}


@app.get('/api/content/version')
def version():
    return {'content_version': '2026.08.29', 'frontend': 'github-pages-ready'}


@app.post('/api/prayer-intentions', status_code=201)
def create_prayer(payload: PrayerIn, db: Session = Depends(get_db)):
    if payload.website:
        return {'status': 'accepted'}
    row = PrayerIntention(name=(payload.name or '').strip() or None, intention=payload.intention.strip())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {'status': 'received', 'id': row.id}


@app.post('/api/contact', status_code=201)
def create_contact(payload: ContactIn, db: Session = Depends(get_db)):
    if payload.website:
        return {'status': 'accepted'}
    row = ContactMessage(
        name=payload.name.strip(),
        email=str(payload.email),
        subject=payload.subject.strip(),
        message=payload.message.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {'status': 'received', 'id': row.id}


@app.post('/api/save-one-soul/join', status_code=201)
def campaign_join(payload: CampaignIn, db: Session = Depends(get_db)):
    digest = token_hash(payload.token)
    row = db.query(SaveOneSoulParticipant).filter_by(token_hash=digest).first()
    if not row:
        row = SaveOneSoulParticipant(token_hash=digest, language=payload.language)
        db.add(row)
    elif row.language != payload.language:
        row.language = payload.language
    db.commit()
    db.refresh(row)
    return progress_payload(row)


@app.post('/api/save-one-soul/day')
def campaign_day(payload: CampaignDayIn, db: Session = Depends(get_db)):
    row = get_participant(db, payload.token)
    setattr(row, f"day{payload.day}", True)
    row.language = payload.language
    if all(bool(getattr(row, f"day{i}")) for i in range(1, 8)) and row.completed_at is None:
        row.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return progress_payload(row)


@app.post('/api/save-one-soul/complete')
def campaign_complete(payload: CampaignIn, db: Session = Depends(get_db)):
    row = get_participant(db, payload.token)
    if not all(bool(getattr(row, f"day{i}")) for i in range(1, 8)):
        raise HTTPException(status_code=409, detail="complete_all_seven_days_first")
    if row.completed_at is None:
        row.completed_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(row)
    return progress_payload(row)


@app.get('/api/save-one-soul/status/{token}')
def campaign_status(token: str, db: Session = Depends(get_db)):
    if len(token) < 20 or len(token) > 128:
        raise HTTPException(status_code=400, detail="invalid_token")
    return progress_payload(get_participant(db, token))


@app.get('/api/save-one-soul/stats')
def campaign_stats(db: Session = Depends(get_db)):
    joined = db.query(func.count(SaveOneSoulParticipant.id)).scalar() or 0
    completed = db.query(func.count(SaveOneSoulParticipant.id)).filter(SaveOneSoulParticipant.completed_at.isnot(None)).scalar() or 0
    english = db.query(func.count(SaveOneSoulParticipant.id)).filter(SaveOneSoulParticipant.language == 'en').scalar() or 0
    khasi = db.query(func.count(SaveOneSoulParticipant.id)).filter(SaveOneSoulParticipant.language == 'kha').scalar() or 0
    days = {}
    for i in range(1, 8):
        days[str(i)] = db.query(func.count(SaveOneSoulParticipant.id)).filter(getattr(SaveOneSoulParticipant, f"day{i}").is_(True)).scalar() or 0
    return {
        'joined': joined,
        'completed': completed,
        'english': english,
        'khasi': khasi,
        'day_completions': days,
        'privacy': 'anonymous_aggregate_only',
    }
