"""
InsuranceOS — WhatsApp Tool (Meta Cloud API)
"""
import os
import logging
import httpx
from typing import Optional

logger = logging.getLogger("insuranceos.whatsapp")

TOKEN = os.getenv("WHATSAPP_TOKEN", "")
PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
BASE_URL = f"https://graph.facebook.com/v19.0/{PHONE_NUMBER_ID}/messages"


def _headers():
    return {
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json",
    }


async def send_text(to: str, text: str) -> dict:
    """Send plain text message."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "text",
        "text": {"body": text},
    }
    return await _post(payload)


async def send_buttons(to: str, body: str, buttons: list[dict]) -> dict:
    """
    Send interactive button message.
    buttons: [{"id": "btn_id", "title": "Label"}]
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {"type": "reply", "reply": btn}
                    for btn in buttons[:3]  # Max 3 buttons
                ]
            },
        },
    }
    return await _post(payload)


async def send_list(to: str, body: str, button_label: str, sections: list[dict]) -> dict:
    """
    Send interactive list message.
    sections: [{"title": "...", "rows": [{"id": "...", "title": "...", "description": "..."}]}]
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": button_label,
                "sections": sections,
            },
        },
    }
    return await _post(payload)


async def send_document(to: str, url: str, filename: str, caption: str = "") -> dict:
    """Send document (PDF proposal/policy)."""
    payload = {
        "messaging_product": "whatsapp",
        "to": to,
        "type": "document",
        "document": {
            "link": url,
            "filename": filename,
            "caption": caption,
        },
    }
    return await _post(payload)


async def mark_as_read(message_id: str) -> dict:
    """Mark message as read."""
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }
    return await _post(payload)


async def _post(payload: dict) -> dict:
    if not TOKEN or not PHONE_NUMBER_ID:
        logger.warning("WhatsApp não configurado (WHATSAPP_TOKEN / WHATSAPP_PHONE_NUMBER_ID ausentes)")
        return {"status": "not_configured"}

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            r = await client.post(BASE_URL, headers=_headers(), json=payload)
            r.raise_for_status()
            return r.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"WhatsApp API error: {e.response.status_code} — {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"WhatsApp send error: {e}")
            raise
