"""Post selected feast days to an authorized Facebook Page and WhatsApp recipient.

Requires an approved WhatsApp template with three BODY text variables:
saint name, feast date, and profile URL. No recipient data is stored here.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime
from html.parser import HTMLParser
import json
import os
from pathlib import Path
import re
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo

DIRECTORY = Path(__file__).resolve().parents[1] / "pages" / "saints.html"
SITE = "https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/pages/"
MONTHS = {datetime(2000, n, 1).strftime("%B"): n for n in range(1, 13)}


class FeastParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.entries: list[dict[str, str]] = []
        self.current: dict[str, str] | None = None
        self.capture = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        attr = dict(attrs)
        if tag == "article" and "saint-item" in (attr.get("class") or "").split():
            self.current = {"id": attr.get("id") or "", "name": "", "feast": ""}
        elif self.current is not None and tag == "h3":
            self.capture = "name"
        elif self.current is not None and tag == "span" and "badge" in (attr.get("class") or "").split():
            self.capture = "feast"

    def handle_data(self, data: str) -> None:
        if self.current is not None and self.capture:
            self.current[self.capture] += data

    def handle_endtag(self, tag: str) -> None:
        if tag in {"h3", "span"}:
            self.capture = ""
        elif tag == "article" and self.current is not None:
            self.entries.append(self.current)
            self.current = None


def feasts_on(day: date) -> list[dict[str, str]]:
    parser = FeastParser()
    parser.feed(DIRECTORY.read_text(encoding="utf-8"))
    result = []
    for entry in parser.entries:
        match = re.fullmatch(r"Feast:\s+([A-Za-z]+)\s+(\d{1,2})", entry["feast"].strip())
        if match and MONTHS.get(match[1]) == day.month and int(match[2]) == day.day:
            result.append({"name": entry["name"].strip(), "date": f"{match[1]} {match[2]}",
                           "url": SITE + "saint.html?id=" + entry["id"]})
    return result


def post_json(url: str, token: str, payload: dict) -> None:
    request = Request(url, data=json.dumps(payload).encode(),
                      headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
                      method="POST")
    with urlopen(request, timeout=25) as response:
        if response.status not in (200, 201):
            raise RuntimeError(f"Meta returned HTTP {response.status}")


def deliver(entries: list[dict[str, str]], dry_run: bool) -> None:
    if not entries:
        print("No featured feast in the directory today.")
        return
    for entry in entries:
        print(f"Selected: {entry['name']} — {entry['date']} — {entry['url']}")
    if dry_run:
        print("Dry run: no messages or Page posts sent.")
        return
    phone_url = os.getenv("WHATSAPP_API_URL", "")
    phone_token = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
    recipient = os.getenv("SAINT_REMINDER_WHATSAPP_RECIPIENT", "")
    template = os.getenv("SAINT_REMINDER_WHATSAPP_TEMPLATE", "")
    page_id = os.getenv("SAINT_REMINDER_FACEBOOK_PAGE_ID", "")
    page_token = os.getenv("SAINT_REMINDER_FACEBOOK_PAGE_TOKEN", "")
    graph_version = (os.getenv("SAINT_REMINDER_GRAPH_VERSION") or "v23.0")
    if not (phone_url and phone_token and recipient and template):
        print("WhatsApp skipped: approved template, recipient, or API settings absent.")
    else:
        if not re.fullmatch(r"https://graph\.facebook\.com/v\d+\.\d+/\d+/messages", phone_url):
            raise ValueError("WHATSAPP_API_URL must be the Meta Graph messages endpoint")
        if not re.fullmatch(r"[+\d]{8,20}", recipient):
            raise ValueError("WhatsApp recipient must be an international phone number")
        for entry in entries:
            post_json(phone_url, phone_token, {"messaging_product": "whatsapp", "to": recipient,
                "type": "template", "template": {"name": template,
                    "language": {"code": (os.getenv("SAINT_REMINDER_WHATSAPP_LANGUAGE") or "en_US")},
                    "components": [{"type": "body", "parameters": [
                        {"type": "text", "text": entry[value]} for value in ("name", "date", "url")]}]}})
            print(f"WhatsApp template submitted for {entry['name']}.")
    if not (page_id and page_token):
        print("Facebook skipped: Page ID or Page access token absent.")
    else:
        if not re.fullmatch(r"\d+", page_id) or not re.fullmatch(r"v\d+\.\d+", graph_version):
            raise ValueError("Invalid Facebook Page ID or Graph version")
        for entry in entries:
            message = f"Today’s featured saint: {entry['name']} ({entry['date']}). Read the story: {entry['url']}"
            post_json(f"https://graph.facebook.com/{graph_version}/{page_id}/feed", page_token,
                      {"message": message})
            print(f"Facebook Page post submitted for {entry['name']}.")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--date", help="YYYY-MM-DD; dry-run only")
    args = parser.parse_args()
    if args.date and not args.dry_run:
        parser.error("--date requires --dry-run")
    day = date.fromisoformat(args.date) if args.date else datetime.now(ZoneInfo("Asia/Kolkata")).date()
    try:
        deliver(feasts_on(day), args.dry_run)
    except (HTTPError, URLError) as exc:
        # Never include Graph response bodies or tokens in public Actions logs.
        raise SystemExit(f"Meta delivery failed: {type(exc).__name__}; check credentials and template approval") from None


if __name__ == "__main__":
    main()
