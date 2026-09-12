import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from .cms_admin import _require_write_guard, require_admin
from .db import Base, get_db

router = APIRouter()


def utcnow():
    return datetime.now(timezone.utc)


class PrayerNetworkRequest(Base):
    __tablename__ = "prayer_network_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    intention: Mapped[str] = mapped_column(Text)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    language: Mapped[str] = mapped_column(String(8), default="en")
    share_worldwide: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_name_sharing: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(24), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    distributed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PrayerDistributionLog(Base):
    __tablename__ = "prayer_distribution_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    prayer_id: Mapped[int] = mapped_column(index=True)
    partner_key: Mapped[str] = mapped_column(String(80))
    status: Mapped[str] = mapped_column(String(24), default="shared")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class MassIntentionRequest(Base):
    __tablename__ = "mass_intention_requests"

    id: Mapped[int] = mapped_column(primary_key=True)
    requester_name: Mapped[str] = mapped_column(String(120))
    requester_email: Mapped[str] = mapped_column(String(254))
    intention_for_name: Mapped[str] = mapped_column(String(180))
    intention_text: Mapped[str] = mapped_column(Text)
    life_status: Mapped[str] = mapped_column(String(16), default="living")
    masses_requested: Mapped[int] = mapped_column(default=1)
    consent_priest_distribution: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(24), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)


class PriestRegistration(Base):
    __tablename__ = "priest_registrations"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(160))
    email: Mapped[str] = mapped_column(String(254), unique=True, index=True)
    country: Mapped[str] = mapped_column(String(100))
    diocese_or_institute: Mapped[str] = mapped_column(String(220))
    parish_or_community: Mapped[str | None] = mapped_column(String(220), nullable=True)
    bishop_or_superior: Mapped[str] = mapped_column(String(220))
    verification_contact: Mapped[str] = mapped_column(String(254))
    declaration_authorized: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String(24), default="pending", index=True)
    active: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class MassAssignment(Base):
    __tablename__ = "mass_assignments"

    id: Mapped[int] = mapped_column(primary_key=True)
    mass_request_id: Mapped[int] = mapped_column(index=True)
    priest_id: Mapped[int] = mapped_column(index=True)
    status: Mapped[str] = mapped_column(String(24), default="offered", index=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    celebrated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


PRAYER_PARTNERS = [
    {
        "key": "charis-international",
        "name": "CHARIS Intercession Commission",
        "url": "https://www.charis.international/en/intercession-commission/",
        "mode": "manual",
        "note": "Official CHARIS prayer-intention channel. Use only with the submitter's explicit sharing consent until an official API/partnership is agreed.",
    },
    {
        "key": "charis-asia",
        "name": "CHARIS Asia Intercession Network",
        "url": "https://www.charisasia.org/intercession",
        "mode": "manual",
        "note": "CHARIS Asia publicly receives names and prayer requests. Manual sharing only unless CHARIS provides an approved integration.",
    },
    {
        "key": "ewtn-prayer",
        "name": "EWTN Prayer Requests",
        "url": "https://www.ewtn.com/catholicism/prayer-requests",
        "mode": "manual",
        "note": "EWTN accepts prayer requests for remembrance by the Franciscan Missionaries of the Eternal Word.",
    },
    {
        "key": "divine-mercy-prayerline",
        "name": "Divine Mercy Intercessory Prayerline",
        "url": "https://thedivinemercy.org/prayer/meet",
        "mode": "manual",
        "note": "The Marian Fathers' Divine Mercy Prayerline receives intentions electronically and remembers them in prayer and Masses.",
    },
    {
        "key": "national-shrine-prayer",
        "name": "Basilica of the National Shrine of the Immaculate Conception",
        "url": "https://secure.nationalshrine.org/site/SPageServer?pagename=prayer_request",
        "mode": "manual",
        "note": "The National Shrine accepts prayer requests and states that they are remembered in daily Masses and devotions.",
    },
]


class PrayerRequestIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    intention: str = Field(min_length=2, max_length=2000)
    country: str | None = Field(default=None, max_length=100)
    language: str = Field(default="en", pattern="^(en|kha)$")
    share_worldwide: bool = False
    consent_name_sharing: bool = False
    website: str | None = Field(default=None, max_length=200)


class PrayerAdminUpdateIn(BaseModel):
    status: str = Field(pattern="^(new|prayed|distributed|archived)$")


class PrayerDistributionIn(BaseModel):
    partner_key: str = Field(min_length=2, max_length=80)
    note: str | None = Field(default=None, max_length=1000)


class MassIntentionIn(BaseModel):
    requester_name: str = Field(min_length=2, max_length=120)
    requester_email: EmailStr
    intention_for_name: str = Field(min_length=2, max_length=180)
    intention_text: str = Field(min_length=2, max_length=2000)
    life_status: str = Field(default="living", pattern="^(living|deceased|other)$")
    masses_requested: int = Field(default=1, ge=1, le=30)
    consent_priest_distribution: bool
    website: str | None = Field(default=None, max_length=200)


class PriestRegistrationIn(BaseModel):
    full_name: str = Field(min_length=3, max_length=160)
    email: EmailStr
    country: str = Field(min_length=2, max_length=100)
    diocese_or_institute: str = Field(min_length=2, max_length=220)
    parish_or_community: str | None = Field(default=None, max_length=220)
    bishop_or_superior: str = Field(min_length=2, max_length=220)
    verification_contact: str = Field(min_length=3, max_length=254)
    declaration_authorized: bool
    website: str | None = Field(default=None, max_length=200)


class PriestVerificationIn(BaseModel):
    status: str = Field(pattern="^(verified|rejected|pending)$")


class MassAssignIn(BaseModel):
    priest_id: int = Field(gt=0)
    note: str | None = Field(default=None, max_length=1000)


class MassAssignmentStatusIn(BaseModel):
    status: str = Field(pattern="^(offered|accepted|celebrated|declined|cancelled)$")
    note: str | None = Field(default=None, max_length=1000)


@router.get("/admin/prayer-intentions", include_in_schema=False)
def admin_prayer_intentions_page():
    path = Path(__file__).resolve().parent / "static" / "prayer-intentions.html"
    response = FileResponse(path, media_type="text/html")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    return response


@router.post("/api/prayer-network/requests", status_code=201)
def submit_prayer_request(payload: PrayerRequestIn, db: Session = Depends(get_db)):
    if payload.website:
        return {"status": "accepted"}
    if payload.share_worldwide and not payload.consent_name_sharing:
        raise HTTPException(status_code=400, detail="explicit_name_sharing_consent_required")
    row = PrayerNetworkRequest(
        name=payload.name.strip(),
        intention=payload.intention.strip(),
        country=(payload.country or "").strip() or None,
        language=payload.language,
        share_worldwide=payload.share_worldwide,
        consent_name_sharing=payload.consent_name_sharing,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "status": "received",
        "id": row.id,
        "worldwide_distribution": "eligible" if row.share_worldwide else "mercy_admin_only",
    }


@router.post("/api/mass-intentions", status_code=201)
def submit_mass_intention(payload: MassIntentionIn, db: Session = Depends(get_db)):
    if payload.website:
        return {"status": "accepted"}
    if not payload.consent_priest_distribution:
        raise HTTPException(status_code=400, detail="priest_distribution_consent_required")
    row = MassIntentionRequest(
        requester_name=payload.requester_name.strip(),
        requester_email=str(payload.requester_email),
        intention_for_name=payload.intention_for_name.strip(),
        intention_text=payload.intention_text.strip(),
        life_status=payload.life_status,
        masses_requested=payload.masses_requested,
        consent_priest_distribution=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "status": "received_pending_assignment",
        "id": row.id,
        "masses_requested": row.masses_requested,
        "offering": "not_collected_by_mercy",
    }


@router.post("/api/priest-network/register", status_code=201)
def register_priest(payload: PriestRegistrationIn, db: Session = Depends(get_db)):
    if payload.website:
        return {"status": "accepted"}
    if not payload.declaration_authorized:
        raise HTTPException(status_code=400, detail="priest_declaration_required")
    email = str(payload.email).lower()
    existing = db.query(PriestRegistration).filter(PriestRegistration.email == email).first()
    if existing:
        return {"status": existing.status, "id": existing.id}
    row = PriestRegistration(
        full_name=payload.full_name.strip(),
        email=email,
        country=payload.country.strip(),
        diocese_or_institute=payload.diocese_or_institute.strip(),
        parish_or_community=(payload.parish_or_community or "").strip() or None,
        bishop_or_superior=payload.bishop_or_superior.strip(),
        verification_contact=payload.verification_contact.strip(),
        declaration_authorized=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"status": "pending_verification", "id": row.id}


@router.get("/api/admin/prayer-network/summary")
def admin_prayer_summary(session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    prayer_total = db.query(func.count(PrayerNetworkRequest.id)).scalar() or 0
    share_total = (
        db.query(func.count(PrayerNetworkRequest.id))
        .filter(PrayerNetworkRequest.share_worldwide.is_(True))
        .scalar()
        or 0
    )
    mass_total = db.query(func.count(MassIntentionRequest.id)).scalar() or 0
    priest_pending = (
        db.query(func.count(PriestRegistration.id))
        .filter(PriestRegistration.status == "pending")
        .scalar()
        or 0
    )
    priest_verified = (
        db.query(func.count(PriestRegistration.id))
        .filter(PriestRegistration.status == "verified", PriestRegistration.active.is_(True))
        .scalar()
        or 0
    )
    return {
        "prayer_requests": prayer_total,
        "worldwide_share_eligible": share_total,
        "mass_intentions": mass_total,
        "priests_pending": priest_pending,
        "priests_verified": priest_verified,
    }


@router.get("/api/admin/prayer-network/requests")
def admin_prayer_requests(session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(PrayerNetworkRequest).order_by(PrayerNetworkRequest.created_at.desc()).limit(500).all()
    return {
        "requests": [
            {
                "id": r.id,
                "name": r.name,
                "intention": r.intention,
                "country": r.country,
                "language": r.language,
                "share_worldwide": r.share_worldwide,
                "consent_name_sharing": r.consent_name_sharing,
                "status": r.status,
                "created_at": r.created_at,
                "distributed_at": r.distributed_at,
            }
            for r in rows
        ]
    }


@router.put("/api/admin/prayer-network/requests/{request_id}")
def admin_update_prayer_request(
    request_id: int,
    payload: PrayerAdminUpdateIn,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    row = db.get(PrayerNetworkRequest, request_id)
    if not row:
        raise HTTPException(status_code=404, detail="prayer_request_not_found")
    row.status = payload.status
    if payload.status == "distributed" and row.distributed_at is None:
        row.distributed_at = utcnow()
    db.commit()
    return {"status": row.status, "id": row.id}


@router.get("/api/admin/prayer-network/partners")
def admin_prayer_partners(session: dict = Depends(require_admin)):
    return {"partners": PRAYER_PARTNERS, "automation_policy": "manual_until_official_partner_api_or_written_permission"}


@router.post("/api/admin/prayer-network/requests/{request_id}/distribution", status_code=201)
def admin_record_distribution(
    request_id: int,
    payload: PrayerDistributionIn,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    prayer = db.get(PrayerNetworkRequest, request_id)
    if not prayer:
        raise HTTPException(status_code=404, detail="prayer_request_not_found")
    if not prayer.share_worldwide or not prayer.consent_name_sharing:
        raise HTTPException(status_code=409, detail="worldwide_sharing_not_authorized")
    partner = next((p for p in PRAYER_PARTNERS if p["key"] == payload.partner_key), None)
    if not partner:
        raise HTTPException(status_code=400, detail="unknown_partner")
    row = PrayerDistributionLog(
        prayer_id=prayer.id,
        partner_key=payload.partner_key,
        status="shared",
        note=(payload.note or "").strip() or None,
    )
    db.add(row)
    prayer.status = "distributed"
    prayer.distributed_at = prayer.distributed_at or utcnow()
    db.commit()
    db.refresh(row)
    return {"status": "recorded", "distribution_id": row.id, "partner": partner["name"]}


@router.get("/api/admin/mass-intentions")
def admin_mass_intentions(session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(MassIntentionRequest).order_by(MassIntentionRequest.created_at.desc()).limit(500).all()
    data = []
    for r in rows:
        assignments = db.query(MassAssignment).filter(MassAssignment.mass_request_id == r.id).all()
        data.append(
            {
                "id": r.id,
                "requester_name": r.requester_name,
                "requester_email": r.requester_email,
                "intention_for_name": r.intention_for_name,
                "intention_text": r.intention_text,
                "life_status": r.life_status,
                "masses_requested": r.masses_requested,
                "status": r.status,
                "created_at": r.created_at,
                "assignments": [
                    {
                        "id": a.id,
                        "priest_id": a.priest_id,
                        "status": a.status,
                        "assigned_at": a.assigned_at,
                        "accepted_at": a.accepted_at,
                        "celebrated_at": a.celebrated_at,
                        "note": a.note,
                    }
                    for a in assignments
                ],
            }
        )
    return {"mass_intentions": data, "offering_policy": "Mercy does not collect Mass offerings in this phase."}


@router.get("/api/admin/priest-network")
def admin_priests(session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    rows = db.query(PriestRegistration).order_by(PriestRegistration.created_at.desc()).limit(500).all()
    return {
        "priests": [
            {
                "id": r.id,
                "full_name": r.full_name,
                "email": r.email,
                "country": r.country,
                "diocese_or_institute": r.diocese_or_institute,
                "parish_or_community": r.parish_or_community,
                "bishop_or_superior": r.bishop_or_superior,
                "verification_contact": r.verification_contact,
                "status": r.status,
                "active": r.active,
                "created_at": r.created_at,
                "verified_at": r.verified_at,
            }
            for r in rows
        ]
    }


@router.put("/api/admin/priest-network/{priest_id}")
def admin_verify_priest(
    priest_id: int,
    payload: PriestVerificationIn,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    row = db.get(PriestRegistration, priest_id)
    if not row:
        raise HTTPException(status_code=404, detail="priest_not_found")
    row.status = payload.status
    row.active = payload.status == "verified"
    row.verified_at = utcnow() if payload.status == "verified" else None
    db.commit()
    return {"id": row.id, "status": row.status, "active": row.active}


@router.post("/api/admin/mass-intentions/{mass_request_id}/assign", status_code=201)
def admin_assign_mass(
    mass_request_id: int,
    payload: MassAssignIn,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    mass = db.get(MassIntentionRequest, mass_request_id)
    if not mass:
        raise HTTPException(status_code=404, detail="mass_intention_not_found")
    priest = db.get(PriestRegistration, payload.priest_id)
    if not priest or priest.status != "verified" or not priest.active:
        raise HTTPException(status_code=409, detail="verified_active_priest_required")
    count = db.query(func.count(MassAssignment.id)).filter(
        MassAssignment.mass_request_id == mass.id,
        MassAssignment.status.notin_(["declined", "cancelled"]),
    ).scalar() or 0
    if count >= mass.masses_requested:
        raise HTTPException(status_code=409, detail="all_requested_masses_already_assigned")
    duplicate = db.query(MassAssignment).filter(
        MassAssignment.mass_request_id == mass.id,
        MassAssignment.priest_id == priest.id,
        MassAssignment.status.notin_(["declined", "cancelled"]),
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="priest_already_assigned_to_this_request")
    assignment = MassAssignment(
        mass_request_id=mass.id,
        priest_id=priest.id,
        note=(payload.note or "").strip() or None,
    )
    db.add(assignment)
    mass.status = "assigned"
    db.commit()
    db.refresh(assignment)
    return {"status": "assigned", "assignment_id": assignment.id, "priest": priest.full_name}


@router.put("/api/admin/mass-assignments/{assignment_id}")
def admin_update_mass_assignment(
    assignment_id: int,
    payload: MassAssignmentStatusIn,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    row = db.get(MassAssignment, assignment_id)
    if not row:
        raise HTTPException(status_code=404, detail="mass_assignment_not_found")
    row.status = payload.status
    row.note = (payload.note or "").strip() or row.note
    if payload.status == "accepted" and row.accepted_at is None:
        row.accepted_at = utcnow()
    if payload.status == "celebrated" and row.celebrated_at is None:
        row.celebrated_at = utcnow()
    db.commit()

    mass = db.get(MassIntentionRequest, row.mass_request_id)
    if mass:
        celebrated = db.query(func.count(MassAssignment.id)).filter(
            MassAssignment.mass_request_id == mass.id,
            MassAssignment.status == "celebrated",
        ).scalar() or 0
        if celebrated >= mass.masses_requested:
            mass.status = "completed"
            db.commit()
    return {"id": row.id, "status": row.status}
