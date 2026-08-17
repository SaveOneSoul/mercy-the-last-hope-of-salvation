from __future__ import annotations
import hashlib
from openai import OpenAI
from .settings import settings
from .schemas import ScopeDecision, CatholicAnswer, Scope, SourceRef, ChatResponse
from .prompts import CLASSIFIER_INSTRUCTIONS, ANSWER_INSTRUCTIONS
from .catholic_guard import local_scope, contains_injection, is_pastoral_safety
from .knowledge import retrieve, build_context

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


def _client() -> OpenAI | None:
    if not settings.openai_api_key:
        return None
    return OpenAI(api_key=settings.openai_api_key)


def _safety_identifier(client_id: str | None) -> str | None:
    if not client_id:
        return None
    return "mercy_" + hashlib.sha256(client_id.encode("utf-8")).hexdigest()[:32]


def classify_scope(message: str, client_id: str | None = None) -> ScopeDecision:
    # Deterministic fail-closed rules run first.
    if contains_injection(message):
        return ScopeDecision(scope=Scope.out_of_scope, confidence=1.0, reason="Prompt-injection or scope-bypass pattern detected.")
    if is_pastoral_safety(message):
        return ScopeDecision(scope=Scope.pastoral_safety, confidence=1.0, reason="Urgent pastoral-safety terms detected.")

    client = _client()
    if client is None:
        scope = Scope(local_scope(message))
        return ScopeDecision(scope=scope, confidence=0.7 if scope == Scope.catholic else 0.95, reason="Local fail-closed scope gate.")

    kwargs = {
        "model": settings.openai_classifier_model,
        "instructions": CLASSIFIER_INSTRUCTIONS,
        "input": message,
        "text_format": ScopeDecision,
        "reasoning": {"effort": "low"},
    }
    safety_id = _safety_identifier(client_id)
    if safety_id:
        kwargs["safety_identifier"] = safety_id
    response = client.responses.parse(**kwargs)
    decision = response.output_parsed
    if decision is None:
        return ScopeDecision(scope=Scope.out_of_scope, confidence=1.0, reason="Classifier returned no structured result.")
    # Fail closed on weak confidence.
    if decision.confidence < 0.70:
        return ScopeDecision(scope=Scope.out_of_scope, confidence=decision.confidence, reason="Classifier confidence below threshold.")
    return decision


def answer_catholic_question(message: str, client_id: str | None = None) -> ChatResponse:
    decision = classify_scope(message, client_id)
    if decision.scope == Scope.out_of_scope:
        return ChatResponse(reply=OUT_OF_SCOPE_REPLY, scope=Scope.out_of_scope, sources=[], needs_human_follow_up=False)
    if decision.scope == Scope.pastoral_safety:
        return ChatResponse(reply=PASTORAL_SAFETY_REPLY, scope=Scope.pastoral_safety, sources=[], needs_human_follow_up=True)

    sources = retrieve(message, limit=5)
    if not sources:
        return ChatResponse(reply=INSUFFICIENT_SOURCE_REPLY, scope=Scope.catholic, sources=[], needs_human_follow_up=True)

    client = _client()
    if client is None:
        # No generative AI is available: stay Catholic-only and expose the approved sources, but do not improvise.
        primary = sources[0]
        reply = (
            f'Approved Catholic source found: {primary["title"]}. {primary["summary"]} '
            "The full AI response service is not enabled on this deployment, so I will not add unsourced material."
        )
        return ChatResponse(
            reply=reply,
            scope=Scope.catholic,
            sources=[SourceRef(id=s["id"], title=s["title"], authority=s["authority"], url=s["url"]) for s in sources[:3]],
            needs_human_follow_up=False,
        )

    approved_context = build_context(sources)
    user_input = f"""USER QUESTION:\n{message}\n\nAPPROVED CATHOLIC CONTEXT:\n{approved_context}"""
    kwargs = {
        "model": settings.openai_model,
        "instructions": ANSWER_INSTRUCTIONS,
        "input": user_input,
        "text_format": CatholicAnswer,
        "reasoning": {"effort": "low"},
    }
    safety_id = _safety_identifier(client_id)
    if safety_id:
        kwargs["safety_identifier"] = safety_id
    response = client.responses.parse(**kwargs)
    result = response.output_parsed
    if result is None or not result.catholic_scope_confirmed:
        return ChatResponse(reply=INSUFFICIENT_SOURCE_REPLY, scope=Scope.catholic, sources=[], needs_human_follow_up=True)

    allowed_ids = {s["id"] for s in sources}
    valid_ids = [sid for sid in result.source_ids if sid in allowed_ids]
    if not valid_ids:
        return ChatResponse(reply=INSUFFICIENT_SOURCE_REPLY, scope=Scope.catholic, sources=[], needs_human_follow_up=True)

    refs = [
        SourceRef(id=s["id"], title=s["title"], authority=s["authority"], url=s["url"])
        for s in sources if s["id"] in valid_ids
    ]
    return ChatResponse(
        reply=result.answer.strip(),
        scope=Scope.catholic,
        sources=refs,
        needs_human_follow_up=result.needs_human_follow_up,
    )
