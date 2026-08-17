from __future__ import annotations
import re
from dataclasses import dataclass

CATHOLIC_TERMS = {
    "catholic", "catechism", "church", "magisterium", "pope", "bishop", "priest", "deacon",
    "vatican", "mass", "eucharist", "communion", "confession", "reconciliation", "penance",
    "baptism", "confirmation", "matrimony", "marriage", "holy orders", "anointing", "sacrament",
    "jesus", "christ", "trinity", "father", "holy spirit", "mary", "our lady", "rosary", "chaplet",
    "divine mercy", "faustina", "saint", "saints", "scripture", "bible", "gospel", "apostle",
    "pentecost", "charism", "charismatic", "charis", "adoration", "novena", "liturgy", "lent",
    "easter", "advent", "purgatory", "heaven", "hell", "sin", "grace", "salvation", "mercy",
    "prayer", "intercession", "relic", "apparition", "private revelation", "canon law", "annulment",
    "evangelization", "catechesis", "vocation", "religious life", "tabernacle", "monstrance",
    "seven sorrows", "stations of the cross", "sacred heart", "immaculate heart"
}

CLEAR_NON_CATHOLIC_TASK_TERMS = {
    "python", "javascript", "typescript", "java code", "c++", "powershell", "sql query", "docker",
    "stock price", "crypto", "bitcoin", "weather", "football score", "cricket score", "recipe",
    "movie review", "gaming", "windows error", "android studio", "git command", "cybersecurity exploit",
    "insurance policy", "investment advice", "travel itinerary", "hotel", "restaurant"
}

PROMPT_INJECTION_PATTERNS = [
    r"ignore (all|any|the|your) (previous|prior|system|developer|catholic)",
    r"reveal (the )?(system|developer) prompt",
    r"act as (?!a catholic|an orthodox catholic)",
    r"do not follow (the )?(rules|instructions)",
    r"bypass (the )?(guard|filter|policy|scope)",
]

PASTORAL_SAFETY_TERMS = {
    "suicide", "kill myself", "self harm", "self-harm", "abuse", "being abused", "rape", "assault",
    "immediate danger", "emergency", "overdose"
}


def normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.lower()).strip()


def contains_injection(text: str) -> bool:
    q = normalize(text)
    return any(re.search(pattern, q) for pattern in PROMPT_INJECTION_PATTERNS)


def has_catholic_signal(text: str) -> bool:
    q = normalize(text)
    return any(term in q for term in CATHOLIC_TERMS)


def is_obviously_non_catholic(text: str) -> bool:
    q = normalize(text)
    catholic = has_catholic_signal(q)
    non_catholic_hits = sum(1 for term in CLEAR_NON_CATHOLIC_TASK_TERMS if term in q)
    return non_catholic_hits > 0 and not catholic


def is_pastoral_safety(text: str) -> bool:
    q = normalize(text)
    return any(term in q for term in PASTORAL_SAFETY_TERMS)


def local_scope(text: str) -> str:
    """Fail closed when the AI classifier is unavailable."""
    if contains_injection(text):
        return "out_of_scope"
    if is_pastoral_safety(text):
        return "pastoral_safety"
    if is_obviously_non_catholic(text):
        return "out_of_scope"
    if has_catholic_signal(text):
        return "catholic"
    return "out_of_scope"
