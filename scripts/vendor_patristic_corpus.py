#!/usr/bin/env python3
"""Vendor public-domain patristic texts into the repository.

This importer downloads only source-locked public-domain editions declared in
data/patristic-corpus-sources.json. It converts each source into stable local
JSON so the deployed site reads from the repository and never depends on an
external site at runtime.

The importer deliberately keeps provenance and does not pretend that lost works
(such as Origen's Hexapla) survive complete.
"""
from __future__ import annotations

import hashlib
import html
import json
import re
import shutil
import urllib.request
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
MANIFEST = ROOT / "data" / "patristic-corpus-sources.json"
OUT = ROOT / "data" / "patristic-corpus"
USER_AGENT = "SaveOneSoul-Patristic-Corpus-Vendor/1.0"

SPACE_RE = re.compile(r"[ \t\r\f\v]+")
BLANK_RE = re.compile(r"\n{3,}")
PAGE_NUMBER_RE = re.compile(r"^\s*(?:[ivxlcdm]+|\d+)\s*$", re.I)


@dataclass
class Block:
    kind: str
    text: str


class GutenbergHTML(HTMLParser):
    """Extract readable structural blocks from Project Gutenberg HTML."""

    BLOCK_TAGS = {"h1", "h2", "h3", "h4", "h5", "p", "li", "blockquote", "pre"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.stack: list[str] = []
        self.buf: list[str] = []
        self.blocks: list[Block] = []
        self.skip_depth = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "nav"}:
            self.skip_depth += 1
            return
        if self.skip_depth:
            return
        self.stack.append(tag)
        if tag == "br":
            self.buf.append("\n")

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag in {"script", "style", "nav"}:
            if self.skip_depth:
                self.skip_depth -= 1
            return
        if self.skip_depth:
            return
        if tag in self.BLOCK_TAGS:
            text = clean_text("".join(self.buf))
            self.buf.clear()
            if text and not PAGE_NUMBER_RE.fullmatch(text):
                kind = "heading" if tag.startswith("h") else "paragraph"
                self.blocks.append(Block(kind, text))
        if self.stack:
            # Pop through malformed/nested markup safely.
            while self.stack:
                current = self.stack.pop()
                if current == tag:
                    break

    def handle_data(self, data: str) -> None:
        if self.skip_depth:
            return
        if self.stack and any(tag in self.BLOCK_TAGS for tag in self.stack):
            self.buf.append(data)


def clean_text(value: str) -> str:
    value = html.unescape(value).replace("\xa0", " ")
    value = SPACE_RE.sub(" ", value)
    value = re.sub(r" *\n *", "\n", value)
    return value.strip()


def download(url: str) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=180) as response:
        data = response.read()
    if len(data) < 1000:
        raise RuntimeError(f"Downloaded source is unexpectedly small: {url}")
    return data


def strip_gutenberg_boilerplate(blocks: list[Block]) -> list[Block]:
    start = 0
    end = len(blocks)
    for i, block in enumerate(blocks):
        if "START OF THE PROJECT GUTENBERG EBOOK" in block.text.upper():
            start = i + 1
            break
    for i in range(start, len(blocks)):
        if "END OF THE PROJECT GUTENBERG EBOOK" in blocks[i].text.upper():
            end = i
            break
    return blocks[start:end]


def group_sections(blocks: list[Block]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current = {"heading": "Front matter", "paragraphs": []}
    for block in blocks:
        if block.kind == "heading":
            if current["paragraphs"] or current["heading"] != "Front matter":
                sections.append(current)
            current = {"heading": block.text, "paragraphs": []}
        else:
            current["paragraphs"].append(block.text)
    if current["paragraphs"] or current["heading"] != "Front matter":
        sections.append(current)
    # Remove empty/obvious navigation sections.
    return [s for s in sections if s["paragraphs"] or len(s["heading"]) > 2]


def slug(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9]+", "-", value).strip("-")
    return value[:96] or "section"


def write_source(source: dict[str, Any]) -> dict[str, Any]:
    raw = download(source["source_url"])
    digest = hashlib.sha256(raw).hexdigest()
    parser = GutenbergHTML()
    parser.feed(raw.decode("utf-8", errors="replace"))
    blocks = strip_gutenberg_boilerplate(parser.blocks)
    sections = group_sections(blocks)
    if len(sections) < 5:
        raise RuntimeError(f"Too few sections parsed from {source['id']}: {len(sections)}")

    target = OUT / source["corpus"] / source["id"]
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    toc: list[dict[str, Any]] = []
    used: dict[str, int] = {}
    total_words = 0
    for index, section in enumerate(sections, 1):
        base = slug(section["heading"])
        used[base] = used.get(base, 0) + 1
        name = base if used[base] == 1 else f"{base}-{used[base]}"
        payload = {
            "source_id": source["id"],
            "index": index,
            "heading": section["heading"],
            "paragraphs": section["paragraphs"],
        }
        words = sum(len(p.split()) for p in section["paragraphs"])
        total_words += words
        filename = f"{index:04d}-{name}.json"
        (target / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        toc.append({"index": index, "heading": section["heading"], "file": filename, "words": words})

    metadata = {
        "id": source["id"],
        "title": source["title"],
        "author_label": source.get("author_label"),
        "edition": source.get("edition"),
        "translators": source.get("translators"),
        "publication_year": source.get("publication_year"),
        "rights": source.get("rights"),
        "source_url": source["source_url"],
        "gutenberg_id": source.get("gutenberg_id"),
        "caution": source.get("caution"),
        "expected_works": source.get("expected_works", []),
        "sha256": digest,
        "section_count": len(toc),
        "word_count": total_words,
        "toc": toc,
    }
    (target / "index.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return {
        "id": source["id"],
        "corpus": source["corpus"],
        "title": source["title"],
        "index": f"{source['corpus']}/{source['id']}/index.json",
        "sections": len(toc),
        "words": total_words,
        "sha256": digest,
    }


def main() -> int:
    config = json.loads(MANIFEST.read_text(encoding="utf-8"))
    OUT.mkdir(parents=True, exist_ok=True)
    results = [write_source(source) for source in config["sources"]]
    index = {
        "schema": 1,
        "generated_by": "scripts/vendor_patristic_corpus.py",
        "runtime_network_required": False,
        "sources": results,
        "lost_or_fragmentary": config.get("lost_or_fragmentary", []),
    }
    (OUT / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"Vendored {len(results)} public-domain source volumes.")
    print(f"Local corpus index: {OUT / 'index.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
