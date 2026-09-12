import hashlib
import hmac
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, String, func
from sqlalchemy.orm import Mapped, Session, mapped_column

from .cms_admin import _require_write_guard, require_admin
from .db import Base, get_db
from .prayer_network import MassAssignment, MassIntentionRequest, PriestRegistration

router = APIRouter()

PRIEST_COOKIE = "mercy_priest_session"
INVITE_TTL_HOURS = 168
SESSION_TTL_DAYS = 30


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _secret() -> bytes:
    value = os.getenv("ADMIN_SESSION_SECRET", "")
    if not value:
        raise HTTPException(status_code=503, detail="priest_portal_not_configured")
    return value.encode("utf-8")


def _csrf_for(token: str) -> str:
    return hmac.new(_secret(), ("priest-csrf:" + token).encode("utf-8"), hashlib.sha256).hexdigest()


class PriestPortalInvite(Base):
    __tablename__ = "priest_portal_invites"

    id: Mapped[int] = mapped_column(primary_key=True)
    priest_id: Mapped[int] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PriestPortalSession(Base):
    __tablename__ = "priest_portal_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    priest_id: Mapped[int] = mapped_column(index=True)
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class PriestActivateIn(BaseModel):
    token: str = Field(min_length=32, max_length=256)


class PriestAssignmentUpdateIn(BaseModel):
    status: str = Field(pattern="^(accepted|celebrated|declined)$")
    note: str | None = Field(default=None, max_length=1000)


def _same_origin_guard(request: Request) -> None:
    origin = request.headers.get("origin", "")
    if origin:
        expected = f"{request.url.scheme}://{request.url.netloc}"
        if origin.rstrip("/") != expected.rstrip("/"):
            raise HTTPException(status_code=403, detail="origin_failed")


def _session(request: Request, db: Session) -> tuple[PriestPortalSession, PriestRegistration, str]:
    raw = request.cookies.get(PRIEST_COOKIE, "")
    if not raw:
        raise HTTPException(status_code=401, detail="priest_auth_required")
    row = (
        db.query(PriestPortalSession)
        .filter(
            PriestPortalSession.token_hash == _hash(raw),
            PriestPortalSession.revoked_at.is_(None),
            PriestPortalSession.expires_at > utcnow(),
        )
        .first()
    )
    if not row:
        raise HTTPException(status_code=401, detail="priest_session_expired")
    priest = db.get(PriestRegistration, row.priest_id)
    if not priest or priest.status != "verified" or not priest.active:
        raise HTTPException(status_code=403, detail="verified_active_priest_required")
    row.last_seen_at = utcnow()
    db.commit()
    return row, priest, raw


def _write_guard(request: Request, raw_token: str) -> None:
    csrf = request.headers.get("x-csrf-token", "")
    if not csrf or not hmac.compare_digest(csrf, _csrf_for(raw_token)):
        raise HTTPException(status_code=403, detail="csrf_failed")
    _same_origin_guard(request)


def _mass_payload(mass: MassIntentionRequest, assignments: int = 0) -> dict:
    return {
        "id": mass.id,
        "intention_for_name": mass.intention_for_name,
        "intention_text": mass.intention_text,
        "life_status": mass.life_status,
        "masses_requested": mass.masses_requested,
        "active_assignments": assignments,
        "remaining": max(int(mass.masses_requested) - int(assignments), 0),
        "status": mass.status,
        "created_at": mass.created_at,
    }


def _update_mass_completion(db: Session, mass_id: int) -> None:
    mass = db.get(MassIntentionRequest, mass_id)
    if not mass:
        return
    celebrated = db.query(func.count(MassAssignment.id)).filter(
        MassAssignment.mass_request_id == mass.id,
        MassAssignment.status == "celebrated",
    ).scalar() or 0
    active = db.query(func.count(MassAssignment.id)).filter(
        MassAssignment.mass_request_id == mass.id,
        MassAssignment.status.notin_(["declined", "cancelled"]),
    ).scalar() or 0
    if celebrated >= mass.masses_requested:
        mass.status = "completed"
    elif active:
        mass.status = "assigned"
    else:
        mass.status = "new"


@router.get("/priest", include_in_schema=False)
def priest_portal_page():
    path = Path(__file__).resolve().parent / "static" / "priest-portal.html"
    response = FileResponse(path, media_type="text/html")
    response.headers["Cache-Control"] = "no-store"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Robots-Tag"] = "noindex, nofollow"
    return response


@router.post("/api/priest/activate")
def priest_activate(
    payload: PriestActivateIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    """Exchange a one-time invite token for a secure priest session.

    The invitation token is delivered in a URL fragment, which browsers do not send
    to the server. The portal removes the fragment before POSTing the token here, so
    the credential stays out of request URLs, Referer headers and access logs.
    """
    _same_origin_guard(request)
    invite = (
        db.query(PriestPortalInvite)
        .filter(
            PriestPortalInvite.token_hash == _hash(payload.token),
            PriestPortalInvite.used_at.is_(None),
            PriestPortalInvite.revoked_at.is_(None),
            PriestPortalInvite.expires_at > utcnow(),
        )
        .with_for_update()
        .first()
    )
    if not invite:
        raise HTTPException(status_code=400, detail="invalid_or_expired_priest_invite")
    priest = db.get(PriestRegistration, invite.priest_id)
    if not priest or priest.status != "verified" or not priest.active:
        raise HTTPException(status_code=403, detail="verified_active_priest_required")
    raw_session = secrets.token_urlsafe(48)
    session = PriestPortalSession(
        priest_id=priest.id,
        token_hash=_hash(raw_session),
        expires_at=utcnow() + timedelta(days=SESSION_TTL_DAYS),
    )
    invite.used_at = utcnow()
    db.add(session)
    db.commit()
    response.set_cookie(
        PRIEST_COOKIE,
        raw_session,
        max_age=SESSION_TTL_DAYS * 86400,
        httponly=True,
        secure=True,
        samesite="strict",
        path="/",
    )
    return {"activated": True, "priest_id": priest.id, "expires_at": session.expires_at}


@router.post("/api/admin/priest-network/{priest_id}/portal-invite", status_code=201)
def admin_create_priest_invite(
    priest_id: int,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    priest = db.get(PriestRegistration, priest_id)
    if not priest or priest.status != "verified" or not priest.active:
        raise HTTPException(status_code=409, detail="verified_active_priest_required")
    db.query(PriestPortalInvite).filter(
        PriestPortalInvite.priest_id == priest.id,
        PriestPortalInvite.used_at.is_(None),
        PriestPortalInvite.revoked_at.is_(None),
    ).update({"revoked_at": utcnow()}, synchronize_session=False)
    raw = secrets.token_urlsafe(48)
    invite = PriestPortalInvite(
        priest_id=priest.id,
        token_hash=_hash(raw),
        expires_at=utcnow() + timedelta(hours=INVITE_TTL_HOURS),
    )
    db.add(invite)
    db.commit()
    base = f"{request.url.scheme}://{request.url.netloc}"
    return {
        "priest_id": priest.id,
        "priest": priest.full_name,
        "activation_url": f"{base}/priest#activate={raw}",
        "expires_at": invite.expires_at,
        "delivery": "copy_and_send_privately_to_verified_priest",
        "security": "invite_token_is_not_transmitted_until_the_activation_post",
    }


@router.post("/api/admin/priest-network/{priest_id}/portal-revoke")
def admin_revoke_priest_portal(
    priest_id: int,
    request: Request,
    session: dict = Depends(require_admin),
    db: Session = Depends(get_db),
):
    _require_write_guard(request, session)
    now = utcnow()
    db.query(PriestPortalInvite).filter(
        PriestPortalInvite.priest_id == priest_id,
        PriestPortalInvite.revoked_at.is_(None),
    ).update({"revoked_at": now}, synchronize_session=False)
    db.query(PriestPortalSession).filter(
        PriestPortalSession.priest_id == priest_id,
        PriestPortalSession.revoked_at.is_(None),
    ).update({"revoked_at": now}, synchronize_session=False)
    db.commit()
    return {"priest_id": priest_id, "portal_access": "revoked"}


@router.get("/api/priest/me")
def priest_me(request: Request, db: Session = Depends(get_db)):
    _, priest, raw = _session(request, db)
    return {
        "id": priest.id,
        "full_name": priest.full_name,
        "country": priest.country,
        "diocese_or_institute": priest.diocese_or_institute,
        "parish_or_community": priest.parish_or_community,
        "csrf": _csrf_for(raw),
    }


@router.post("/api/priest/logout")
def priest_logout(request: Request, response: Response, db: Session = Depends(get_db)):
    row, _, raw = _session(request, db)
    _write_guard(request, raw)
    row.revoked_at = utcnow()
    db.commit()
    response.delete_cookie(PRIEST_COOKIE, path="/")
    return {"logged_out": True}


@router.get("/api/priest/mass-intentions/available")
def priest_available_mass_intentions(request: Request, db: Session = Depends(get_db)):
    _, priest, _ = _session(request, db)
    rows = (
        db.query(MassIntentionRequest)
        .filter(
            MassIntentionRequest.consent_priest_distribution.is_(True),
            MassIntentionRequest.status.in_(["new", "assigned"]),
        )
        .order_by(MassIntentionRequest.created_at.asc())
        .limit(200)
        .all()
    )
    items = []
    for mass in rows:
        own = db.query(MassAssignment.id).filter(
            MassAssignment.mass_request_id == mass.id,
            MassAssignment.priest_id == priest.id,
            MassAssignment.status.notin_(["declined", "cancelled"]),
        ).first()
        if own:
            continue
        active = db.query(func.count(MassAssignment.id)).filter(
            MassAssignment.mass_request_id == mass.id,
            MassAssignment.status.notin_(["declined", "cancelled"]),
        ).scalar() or 0
        if active < mass.masses_requested:
            items.append(_mass_payload(mass, active))
    return {"items": items, "offering_policy": "Mercy does not collect Mass offerings."}


@router.post("/api/priest/mass-intentions/{mass_request_id}/claim", status_code=201)
def priest_claim_mass_intention(mass_request_id: int, request: Request, db: Session = Depends(get_db)):
    _, priest, raw = _session(request, db)
    _write_guard(request, raw)
    mass = (
        db.query(MassIntentionRequest)
        .filter(MassIntentionRequest.id == mass_request_id)
        .with_for_update()
        .first()
    )
    if not mass or not mass.consent_priest_distribution:
        raise HTTPException(status_code=404, detail="mass_intention_not_available")
    duplicate = db.query(MassAssignment).filter(
        MassAssignment.mass_request_id == mass.id,
        MassAssignment.priest_id == priest.id,
        MassAssignment.status.notin_(["declined", "cancelled"]),
    ).first()
    if duplicate:
        raise HTTPException(status_code=409, detail="mass_intention_already_claimed_by_priest")
    active = db.query(func.count(MassAssignment.id)).filter(
        MassAssignment.mass_request_id == mass.id,
        MassAssignment.status.notin_(["declined", "cancelled"]),
    ).scalar() or 0
    if active >= mass.masses_requested:
        raise HTTPException(status_code=409, detail="all_requested_masses_already_assigned")
    assignment = MassAssignment(
        mass_request_id=mass.id,
        priest_id=priest.id,
        status="accepted",
        accepted_at=utcnow(),
        note="Claimed by verified priest through Mercy Priest Portal",
    )
    db.add(assignment)
    mass.status = "assigned"
    db.commit()
    db.refresh(assignment)
    return {"assignment_id": assignment.id, "status": assignment.status}


@router.get("/api/priest/assignments")
def priest_assignments(request: Request, db: Session = Depends(get_db)):
    _, priest, _ = _session(request, db)
    rows = (
        db.query(MassAssignment)
        .filter(MassAssignment.priest_id == priest.id)
        .order_by(MassAssignment.assigned_at.desc())
        .limit(500)
        .all()
    )
    items = []
    for row in rows:
        mass = db.get(MassIntentionRequest, row.mass_request_id)
        if not mass:
            continue
        items.append(
            {
                "assignment_id": row.id,
                "status": row.status,
                "assigned_at": row.assigned_at,
                "accepted_at": row.accepted_at,
                "celebrated_at": row.celebrated_at,
                "note": row.note,
                "mass": _mass_payload(mass),
            }
        )
    return {"items": items}


@router.put("/api/priest/assignments/{assignment_id}")
def priest_update_assignment(
    assignment_id: int,
    payload: PriestAssignmentUpdateIn,
    request: Request,
    db: Session = Depends(get_db),
):
    _, priest, raw = _session(request, db)
    _write_guard(request, raw)
    row = db.get(MassAssignment, assignment_id)
    if not row or row.priest_id != priest.id:
        raise HTTPException(status_code=404, detail="assignment_not_found")
    if row.status in {"celebrated", "cancelled"}:
        raise HTTPException(status_code=409, detail="assignment_already_closed")
    if payload.status == "celebrated" and row.status not in {"accepted", "offered"}:
        raise HTTPException(status_code=409, detail="assignment_must_be_accepted_before_celebration")
    row.status = payload.status
    if payload.note:
        row.note = payload.note.strip()
    if payload.status == "accepted" and row.accepted_at is None:
        row.accepted_at = utcnow()
    if payload.status == "celebrated" and row.celebrated_at is None:
        row.accepted_at = row.accepted_at or utcnow()
        row.celebrated_at = utcnow()
    _update_mass_completion(db, row.mass_request_id)
    db.commit()
    return {"assignment_id": row.id, "status": row.status, "celebrated_at": row.celebrated_at}
