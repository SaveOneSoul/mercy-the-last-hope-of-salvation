"""Private request-driven AI Ministry service and API.

Uses the existing signed Mercy admin session as the initial owner authentication
boundary. It does not add public navigation and never schedules generation.
"""
import json
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.orm import Mapped, Session, mapped_column

from .ai_ministry_policy import MinistryIdentity, can_access_ministry, private_menu
from .cms_admin import require_admin, _require_write_guard
from .db import Base, get_db
from .magisterium import CatholicChatIn, ask_magisterium
from .gemini_ministry import refine_ministry_text

router = APIRouter(prefix="/api/admin/ministry", tags=["private-ai-ministry"])
TYPES = {"homily", "bible_study", "retreat", "catechesis", "rcia", "lesson_planner", "prayer_service", "liturgy"}


def utcnow():
    return datetime.now(timezone.utc)


class MinistryDraft(Base):
    __tablename__ = "ministry_drafts"
    id: Mapped[int] = mapped_column(primary_key=True)
    owner_subject: Mapped[str] = mapped_column(String(120), index=True)
    kind: Mapped[str] = mapped_column(String(40), index=True)
    title: Mapped[str] = mapped_column(String(240))
    request_text: Mapped[str] = mapped_column(Text)
    content: Mapped[str] = mapped_column(Text)
    grounded_content: Mapped[str | None] = mapped_column(Text, nullable=True)
    orchestration_json: Mapped[str] = mapped_column(Text, default="{}")
    sources_json: Mapped[str] = mapped_column(Text, default="[]")
    status: Mapped[str] = mapped_column(String(20), default="draft", index=True)
    version: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


class GenerateIn(BaseModel):
    kind: str = Field(max_length=40)
    title: str = Field(min_length=1, max_length=240)
    request: str = Field(min_length=2, max_length=5000)


class TransitionIn(BaseModel):
    expected_version: int = Field(ge=1)


class EditIn(BaseModel):
    expected_version: int = Field(ge=1)
    title: str = Field(min_length=1, max_length=240)
    content: str = Field(min_length=1, max_length=60000)


def _owner_identity(session: dict) -> MinistryIdentity:
    # Existing admin authentication is the initial owner-only integration.
    # A later identity provider can populate separate ministry member roles.
    return MinistryIdentity(
        subject="mercy-owner", authenticated=True, channel="web",
        domains=frozenset({"catholic"}), roles=frozenset({"owner"}),
        permissions=frozenset({"ministry:read", "ministry:write", "ministry:publish"}),
    )


def _require(session: dict, action: str) -> MinistryIdentity:
    identity = _owner_identity(session)
    if not can_access_ministry(identity, action):
        raise HTTPException(status_code=403, detail="ministry_forbidden")
    return identity


def _serialize(row: MinistryDraft) -> dict:
    return {
        "id": row.id, "kind": row.kind, "title": row.title, "content": row.content,
        "sources": json.loads(row.sources_json or "[]"), "status": row.status,
        "version": row.version, "created_at": row.created_at, "updated_at": row.updated_at,
        "published_at": row.published_at,
        "orchestration": json.loads(getattr(row, "orchestration_json", "{}") or "{}"),
    }


@router.get("/menu")
def ministry_menu(session: dict = Depends(require_admin)):
    return {"items": private_menu(_require(session, "read"))}


@router.get("/drafts")
def list_drafts(session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    identity = _require(session, "read")
    rows = db.query(MinistryDraft).filter(MinistryDraft.owner_subject == identity.subject).order_by(MinistryDraft.updated_at.desc()).limit(100).all()
    return {"items": [_serialize(row) for row in rows]}


@router.post("/generate", status_code=201)
def generate(payload: GenerateIn, request: Request, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    _require_write_guard(request, session)
    identity = _require(session, "write")
    if payload.kind not in TYPES:
        raise HTTPException(status_code=400, detail="unsupported_ministry_type")
    prompt = (
        "Create a private Catholic ministry draft only because an authorized user explicitly requested it. "
        "Do not claim publication. Distinguish binding doctrine, discipline, theological opinion, devotional practice and private revelation. "
        "Prefer Scripture, Catechism, Magisterium, Church Fathers and Saints; never fabricate citations.\n\n"
        f"TYPE: {payload.kind}\nTITLE: {payload.title.strip()}\nREQUEST: {payload.request.strip()}"
    )
    grounded = ask_magisterium(CatholicChatIn(message=prompt, language="en"), f"ministry:{identity.subject}")
    refined = refine_ministry_text(grounded["reply"], kind=payload.kind, title=payload.title.strip())
    final_text = refined["text"]
    if not final_text.strip():
        raise HTTPException(status_code=502, detail="ministry_validation_failed")
    orchestration = {
        "doctrinal_provider": grounded.get("provider"), "doctrinal_model": grounded.get("model"),
        "editorial_provider": refined.get("provider"), "editorial_model": refined.get("model"),
        "editorial_refined": refined.get("refined", False), "validated": True,
    }
    row = MinistryDraft(
        owner_subject=identity.subject, kind=payload.kind, title=payload.title.strip(),
        request_text=payload.request.strip(), content=final_text, grounded_content=grounded["reply"],
        orchestration_json=json.dumps(orchestration),
        sources_json=json.dumps(grounded.get("sources") or []), status="draft",
    )
    db.add(row); db.commit(); db.refresh(row)
    return _serialize(row)


def _transition(draft_id: int, payload: TransitionIn, request: Request, session: dict, db: Session, target: str):
    _require_write_guard(request, session)
    identity = _require(session, "publish" if target == "published" else "write")
    row = db.get(MinistryDraft, draft_id)
    if not row or row.owner_subject != identity.subject:
        raise HTTPException(status_code=404, detail="ministry_draft_not_found")
    if row.version != payload.expected_version:
        raise HTTPException(status_code=409, detail="ministry_draft_version_conflict")
    if target == "published" and row.status != "reviewed":
        raise HTTPException(status_code=409, detail="review_required_before_publish")
    row.status = target; row.version += 1
    if target == "published": row.published_at = utcnow()
    db.commit(); db.refresh(row)
    return _serialize(row)


@router.post("/drafts/{draft_id}/review")
def review(draft_id: int, payload: TransitionIn, request: Request, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    return _transition(draft_id, payload, request, session, db, "reviewed")


@router.post("/drafts/{draft_id}/publish")
def publish(draft_id: int, payload: TransitionIn, request: Request, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    return _transition(draft_id, payload, request, session, db, "published")


@router.put("/drafts/{draft_id}")
def edit_draft(draft_id: int, payload: EditIn, request: Request, session: dict = Depends(require_admin), db: Session = Depends(get_db)):
    _require_write_guard(request, session)
    identity = _require(session, "write")
    row = db.get(MinistryDraft, draft_id)
    if not row or row.owner_subject != identity.subject:
        raise HTTPException(status_code=404, detail="ministry_draft_not_found")
    if row.status == "published":
        raise HTTPException(status_code=409, detail="published_draft_is_immutable")
    if row.version != payload.expected_version:
        raise HTTPException(status_code=409, detail="ministry_draft_version_conflict")
    row.title = payload.title.strip(); row.content = payload.content.strip(); row.status = "draft"; row.version += 1
    db.commit(); db.refresh(row)
    return _serialize(row)
