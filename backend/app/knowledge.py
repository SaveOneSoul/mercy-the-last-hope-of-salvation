from __future__ import annotations
import json
import re
from pathlib import Path
from functools import lru_cache

DATA_PATH = Path(__file__).with_name("data") / "catholic_knowledge.json"
STOPWORDS = {"the","a","an","and","or","of","to","in","is","are","was","were","be","been","for","on","with","what","why","how","who","when","can","do","does","did","i","me","my","we","our","you","your","it","this","that","about","from"}


def _tokens(text: str) -> set[str]:
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if len(w) > 2 and w not in STOPWORDS}


@lru_cache(maxsize=1)
def load_knowledge() -> list[dict]:
    return json.loads(DATA_PATH.read_text(encoding="utf-8"))


def retrieve(query: str, limit: int = 5) -> list[dict]:
    q_lower = query.lower()
    q_tokens = _tokens(query)
    scored = []
    for item in load_knowledge():
        tag_text = " ".join(item["tags"]).lower()
        full_text = f'{item["title"]} {tag_text} {item["summary"]}'
        tokens = _tokens(full_text)
        score = len(q_tokens & tokens)
        for tag in item["tags"]:
            if tag.lower() in q_lower:
                score += 4
        # Authority/source bonuses do not create a match by themselves.
        if score > 0:
            scored.append((score, item))
    scored.sort(key=lambda x: (-x[0], x[1]["id"]))
    return [item for _, item in scored[:limit]]


def build_context(items: list[dict]) -> str:
    chunks = []
    for item in items:
        chunks.append(
            f'SOURCE_ID: {item["id"]}\n'
            f'TITLE: {item["title"]}\n'
            f'AUTHORITY: {item["authority"]}\n'
            f'URL: {item["url"]}\n'
            f'APPROVED_SUMMARY: {item["summary"]}'
        )
    return "\n\n---\n\n".join(chunks)
