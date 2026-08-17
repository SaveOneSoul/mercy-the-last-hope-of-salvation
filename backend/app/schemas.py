from __future__ import annotations
from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field, EmailStr


class Scope(str, Enum):
    catholic = "catholic"
    pastoral_safety = "pastoral_safety"
    out_of_scope = "out_of_scope"


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    client_id: str | None = Field(default=None, max_length=128)
    recaptcha_token: str | None = Field(default=None, max_length=8192)


class SourceRef(BaseModel):
    id: str
    title: str
    authority: str
    url: str


class DoctrineReference(BaseModel):
    id: str
    topic: str
    ccc: str
    scripture: list[str]
    vatican_url: str


class ChatResponse(BaseModel):
    reply: str
    scope: Scope
    sources: list[SourceRef] = []
    references: list[DoctrineReference] = []
    needs_human_follow_up: bool = False


class ScopeDecision(BaseModel):
    scope: Scope
    confidence: float = Field(ge=0, le=1)
    reason: str = Field(max_length=300)


class CatholicAnswer(BaseModel):
    catholic_scope_confirmed: bool
    answer: str = Field(max_length=5000)
    source_ids: list[str]
    reference_ids: list[str] = []
    needs_human_follow_up: bool = False


class ContactRequest(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=30)
    topic: str = Field(default="Other", max_length=100)
    message: str = Field(min_length=2, max_length=5000)
    consent: Literal["yes"] | None = None
    recaptcha_token: str | None = Field(default=None, max_length=8192)


class ContactResponse(BaseModel):
    accepted: bool
    message: str
    automatic_reply: str | None = None
    delivered_to_owner: bool = False
    stored: bool = False
