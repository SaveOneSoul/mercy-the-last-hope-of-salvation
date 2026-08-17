from __future__ import annotations
import json
import re
from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).with_name("data") / "catholic_reference_map.json"
STOPWORDS = {"the","a","an","and","or","of","to","in","is","are","was","were","be","been","for","on","with","what","why","how","who","when","can","do","does","did","i","me","my","we","our","you","your","it","this","that","about","from","catholic","church","teach","teaches"}

def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}

@lru_cache(maxsize=1)
def load_reference_map() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))

def retrieve_references(query: str, limit: int = 4) -> list[dict]:
    q = query.lower()
    q_tokens = _tokens(query)
    scored: list[tuple[int, dict]] = []
    for item in load_reference_map():
        text = " ".join([item["topic"], item["summary"], *item["keywords"], *item["scripture"], item["ccc"]])
        score = len(q_tokens & _tokens(text))
        for keyword in item["keywords"]:
            if keyword.lower() in q:
                score += 5
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["id"]))
    return [item for _, item in scored[:limit]]

def build_reference_context(items: list[dict]) -> str:
    chunks = []
    for item in items:
        chunks.append(
            f'REFERENCE_ID: {item["id"]}\n'
            f'TOPIC: {item["topic"]}\n'
            f'CCC_PARAGRAPHS: {item["ccc"]}\n'
            f'SCRIPTURE_REFERENCES: {", ".join(item["scripture"])}\n'
            f'VATICAN_URL: {item["vatican_url"]}\n'
            f'APPROVED_SUMMARY: {item["summary"]}'
        )
    return "\n\n---\n\n".join(chunks)
