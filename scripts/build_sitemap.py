#!/usr/bin/env python3
"""Build the public sitemap used by GitHub Pages.

Static routes are discovered from the deployed English/Khasi page trees. Published
CMS routes are fetched from the Mercy API SEO manifest. If the API is temporarily
unavailable, the checked-in sitemap is left untouched so a Pages deployment is not
blocked by a backend outage.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
CONFIG = ROOT / "javascript" / "analytics-config.json"
SITEMAP = ROOT / "sitemap.xml"
SITE_BASE = "https://saveonesoul.github.io/mercy-the-last-hope-of-salvation"
EXCLUDED_TEMPLATES = {"post.html", "content.html"}


def _static_urls() -> list[dict]:
    items = [{"loc": f"{SITE_BASE}/", "priority": "1.0"}]
    for prefix, folder in (("pages", ROOT / "pages"), ("kh/pages", ROOT / "kh" / "pages")):
        if not folder.exists():
            continue
        for path in sorted(folder.glob("*.html")):
            if path.name in EXCLUDED_TEMPLATES:
                continue
            priority = "0.9" if path.name in {"save-one-soul.html", "intentions.html"} else "0.7"
            items.append({"loc": f"{SITE_BASE}/{prefix}/{quote(path.name)}", "priority": priority})
    kh_index = ROOT / "kh" / "index.html"
    if kh_index.exists():
        items.append({"loc": f"{SITE_BASE}/kh/index.html", "priority": "0.9"})
    return items


def _api_base() -> str:
    data = json.loads(CONFIG.read_text(encoding="utf-8"))
    return str(data.get("mercy_api_base") or "").rstrip("/")


def _cms_urls() -> list[dict]:
    base = _api_base()
    if not base:
        raise RuntimeError("Mercy API base is not configured")
    req = Request(
        base + "/api/content/seo-manifest",
        headers={"Accept": "application/json", "User-Agent": "MercySitemapBot/1.0"},
    )
    with urlopen(req, timeout=20) as response:
        payload = json.load(response)
    items = []
    for item in payload.get("items", []):
        loc = str(item.get("url") or "").strip()
        if not loc.startswith(SITE_BASE + "/"):
            continue
        row = {"loc": loc, "priority": "0.8" if item.get("kind") == "post" else "0.7"}
        if item.get("lastmod"):
            row["lastmod"] = str(item["lastmod"])[:10]
        items.append(row)
    return items


def _render(items: list[dict]) -> bytes:
    ET.register_namespace("", "http://www.sitemaps.org/schemas/sitemap/0.9")
    ns = "http://www.sitemaps.org/schemas/sitemap/0.9"
    root = ET.Element(f"{{{ns}}}urlset")
    seen: set[str] = set()
    for item in items:
        loc = item["loc"]
        if loc in seen:
            continue
        seen.add(loc)
        node = ET.SubElement(root, f"{{{ns}}}url")
        ET.SubElement(node, f"{{{ns}}}loc").text = loc
        if item.get("lastmod"):
            ET.SubElement(node, f"{{{ns}}}lastmod").text = item["lastmod"]
        if item.get("priority"):
            ET.SubElement(node, f"{{{ns}}}priority").text = item["priority"]
    return b'<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="utf-8") + b"\n"


def main() -> int:
    static = _static_urls()
    try:
        cms = _cms_urls()
    except Exception as exc:
        print(f"warning: CMS SEO manifest unavailable: {exc}", file=sys.stderr)
        if SITEMAP.exists():
            print("keeping existing sitemap.xml")
            return 0
        cms = []
    data = _render(static + cms)
    SITEMAP.write_bytes(data)
    print(
        f"wrote sitemap.xml with {len(static)} static routes and {len(cms)} CMS routes at "
        f"{datetime.now(timezone.utc).isoformat()}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
