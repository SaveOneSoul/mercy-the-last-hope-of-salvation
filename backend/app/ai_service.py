from __future__ import annotations

from google import genai
from google.genai import types

from .settings import settings
from .schemas import (
    ScopeDecision,
    CatholicAnswer,
    Scope,
    SourceRef,
    DoctrineReference,
    ChatResponse,
)
from .prompts import CLASSIFIER_INSTRUCTIONS, ANSWER_INSTRUCTIONS
from .catholic_guard import local_scope, contains_injection, is_pastoral_safety
from .knowledge import retrieve, build_context
from .reference_service import retrieve_references, build_reference_context

OUT_OF_SCOPE_REPLY = (
    "Mercy Guide is limited to Roman Catholic faith, Sacred Scripture in Catholic context, "
    "doctrine, sacraments, prayer, saints, Divine Mercy, Catholic spiritual life and evangelization. "
    "Please ask a Catholic-related question."
)

INSUFFICIENT_SOURCE_REPLY = (
    "I do not have enough approved Catholic source material in this knowledge base to answer that faithfully. "
    "Please consult the Catechism, an official Church source, or a priest, and you may send the question for human follow-up."
)

PASTORAL_SAFETY_REPLY = (
    "Your safety matters. Mercy Guide cannot handle an urgent crisis as a chatbot. If there is immediate danger, "
    "contact local emergency services or a trusted person who can stay with you, and contact a priest or appropriate "
    "pastoral leader as soon as possible. For non-immediate pastoral support, you may also send a private message through the contact form."
)


def _client() -> genai.Client | None:
    if not settings.gemini_api_key:
        return None
    return genai.Client(api_key=settings.gemini_api_key)


def _parse_structured(response, schema_type):
    parsed = getattr(response, "parsed", None)
    if isinstance(parsed, schema_type):
        return parsed

    text = getattr(response, "text", None)
    if not text:
        return None

    return schema_type.model_validate_json(text)


def classify_scope(message: str, client_id: str | None = None) -> ScopeDecision:
    # Deterministic, fail-closed checks always run before any model call.
    if contains_injection(message):
        return ScopeDecision(
            scope=Scope.out_of_scope,
            confidence=1.0,
            reason="Prompt-injection or scope-bypass pattern detected.",
        )
    if is_pastoral_safety(message):
        return ScopeDecision(
            scope=Scope.pastoral_safety,
            confidence=1.0,
            reason="Urgent pastoral-safety terms detected.",
        )

    client = _client()
    if client is None:
        scope = Scope(local_scope(message))
        return ScopeDecision(
            scope=scope,
            confidence=0.7 if scope == Scope.catholic else 0.95,
            reason="Local fail-closed scope gate.",
        )

    response = client.models.generate_content(
        model=settings.gemini_classifier_model,
        contents=message,
        config=types.GenerateContentConfig(
            system_instruction=CLASSIFIER_INSTRUCTIONS,
            response_mime_type="application/json",
            response_schema=ScopeDecision,
            max_output_tokens=512,
        ),
    )
    decision = _parse_structured(response, ScopeDecision)
    if decision is None:
        return ScopeDecision(
            scope=Scope.out_of_scope,
            confidence=1.0,
            reason="Classifier returned no structured result.",
        )

    # Fail closed on weak confidence.
    if decision.confidence < 0.70:
        return ScopeDecision(
            scope=Scope.out_of_scope,
            confidence=decision.confidence,
            reason="Classifier confidence below threshold.",
        )
    return decision


def answer_catholic_question(
    message: str, client_id: str | None = None
) -> ChatResponse:
    decision = classify_scope(message, client_id)

    if decision.scope == Scope.out_of_scope:
        return ChatResponse(
            reply=OUT_OF_SCOPE_REPLY,
            scope=Scope.out_of_scope,
            sources=[],
            needs_human_follow_up=False,
        )

    if decision.scope == Scope.pastoral_safety:
        return ChatResponse(
            reply=PASTORAL_SAFETY_REPLY,
            scope=Scope.pastoral_safety,
            sources=[],
            needs_human_follow_up=True,
        )

    sources = retrieve(message, limit=5)
    if not sources:
        return ChatResponse(
            reply=INSUFFICIENT_SOURCE_REPLY,
            scope=Scope.catholic,
            sources=[],
            needs_human_follow_up=True,
        )

    client = _client()
    if client is None:
        # No generative AI is available: remain Catholic-only and do not improvise.
        primary = sources[0]
        reply = (
            f'Approved Catholic source found: {primary["title"]}. {primary["summary"]} '
            "The full AI response service is not enabled on this deployment, so I will not add unsourced material."
        )
        return ChatResponse(
            reply=reply,
            scope=Scope.catholic,
            sources=[
                SourceRef(
                    id=s["id"],
                    title=s["title"],
                    authority=s["authority"],
                    url=s["url"],
                )
                for s in sources[:3]
            ],
            needs_human_follow_up=False,
        )

    approved_context = build_context(sources)
    doctrinal_refs = retrieve_references(message, limit=4)
    reference_context = (
        build_reference_context(doctrinal_refs)
        if doctrinal_refs
        else "No approved doctrine-reference mapping matched this question."
    )

    user_input = f"""USER QUESTION:
{message}

APPROVED CATHOLIC CONTEXT:
{approved_context}

APPROVED DOCTRINAL REFERENCE MAP:
{reference_context}"""

    response = client.models.generate_content(
        model=settings.gemini_model,
        contents=user_input,
        config=types.GenerateContentConfig(
            system_instruction=ANSWER_INSTRUCTIONS,
            response_mime_type="application/json",
            response_schema=CatholicAnswer,
            max_output_tokens=4096,
        ),
    )

    result = _parse_structured(response, CatholicAnswer)
    if result is None or not result.catholic_scope_confirmed:
        return ChatResponse(
            reply=INSUFFICIENT_SOURCE_REPLY,
            scope=Scope.catholic,
            sources=[],
            needs_human_follow_up=True,
        )

    allowed_ids = {s["id"] for s in sources}
    valid_ids = [sid for sid in result.source_ids if sid in allowed_ids]
    if not valid_ids:
        return ChatResponse(
            reply=INSUFFICIENT_SOURCE_REPLY,
            scope=Scope.catholic,
            sources=[],
            needs_human_follow_up=True,
        )

    refs = [
        SourceRef(
            id=s["id"],
            title=s["title"],
            authority=s["authority"],
            url=s["url"],
        )
        for s in sources
        if s["id"] in valid_ids
    ]

    allowed_reference_ids = {r["id"] for r in doctrinal_refs}
    valid_reference_ids = [
        rid for rid in result.reference_ids if rid in allowed_reference_ids
    ]
    doctrine_refs = [
        DoctrineReference(
            id=r["id"],
            topic=r["topic"],
            ccc=r["ccc"],
            scripture=r["scripture"],
            vatican_url=r["vatican_url"],
        )
        for r in doctrinal_refs
        if r["id"] in valid_reference_ids
    ]

    return ChatResponse(
        reply=result.answer.strip(),
        scope=Scope.catholic,
        sources=refs,
        references=doctrine_refs,
        needs_human_follow_up=result.needs_human_follow_up,
    )
