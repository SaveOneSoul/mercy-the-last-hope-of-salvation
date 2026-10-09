"""Outbound WhatsApp delivery helper, intentionally disabled until account onboarding.

Call only from a reviewed delivery worker using a claimed outbox job.
Never invoke during webhook processing. All credentials are server-side.
"""
import os
import httpx

WELCOME = ("Greetings in the Name of Jesus Christ! Welcome to Save One Soul — "
           "Divine Mercy Service. Reply MENU to see Divine Mercy, Homilies, "
           "Scripture — Logos, Catholic Formation, Saints and Church Fathers, "
           "or request to speak with the ministry administrator. Jesus, I trust in You!")

MENU = ("Save One Soul ministry services:\n"
        "1. Homilies — https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/pages/homiletics.html\n"
        "2. Divine Mercy — https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/pages/divine-mercy.html\n"
        "3. Scripture — https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/pages/logos.html\n"
        "4. Codex Fidei — https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/pages/codex-fidei.html\n"
        "5. Saints — https://saveonesoul.github.io/mercy-the-last-hope-of-salvation/pages/saints.html\n"
        "Reply HUMAN to ask for personal assistance.")

def outbound_ready():
    return bool(os.getenv("WHATSAPP_OUTBOUND_ENABLED") == "true"
                and os.getenv("WHATSAPP_ACCESS_TOKEN")
                and os.getenv("WHATSAPP_PHONE_NUMBER_ID"))

def send_text(contact_id: str, message: str):
    if not outbound_ready():
        raise RuntimeError("whatsapp_outbound_disabled")
    phone_id = os.environ["WHATSAPP_PHONE_NUMBER_ID"]
    version = os.getenv("WHATSAPP_GRAPH_VERSION", "v23.0")
    with httpx.Client(timeout=15) as client:
        response = client.post(
            f"https://graph.facebook.com/{version}/{phone_id}/messages",
            headers={"Authorization": f"Bearer {os.environ['WHATSAPP_ACCESS_TOKEN']}"},
            json={"messaging_product": "whatsapp", "to": contact_id, "type": "text",
                  "text": {"preview_url": False, "body": message}})
        response.raise_for_status()
        return response.json().get("messages", [])
