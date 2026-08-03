"""
Meta WhatsApp Cloud API client.

Handles sending messages, downloading media, and webhook signature verification.
"""

import hashlib
import hmac
import logging
from typing import Optional, Dict, Any, List

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

BASE_URL = "https://graph.facebook.com/v21.0"


def _headers() -> Dict[str, str]:
    """Authorization headers for the WhatsApp Cloud API."""
    settings = get_settings()
    return {
        "Authorization": f"Bearer {settings.meta_access_token}",
        "Content-Type": "application/json",
    }


def _messages_url() -> str:
    """URL for sending messages."""
    settings = get_settings()
    return f"{BASE_URL}/{settings.meta_phone_number_id}/messages"


# ── Sending Messages ─────────────────────────────────────────


async def send_text_message(phone: str, text: str) -> Dict[str, Any]:
    """
    Send a plain text message to a WhatsApp number.

    Args:
        phone: Recipient phone number in international format (e.g., '919876543210').
        text: Message text.
    """
    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "text",
        "text": {"body": text},
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(_messages_url(), headers=_headers(), json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info("Text message sent to %s", phone)
        return result


async def send_template_message(
    phone: str,
    template_name: str,
    language_code: str = "en",
    parameters: Optional[List[Dict[str, str]]] = None,
) -> Dict[str, Any]:
    """
    Send a template message (pre-approved by Meta).

    Args:
        phone: Recipient phone number.
        template_name: Name of the approved template.
        language_code: Template language code.
        parameters: Template parameter values.
    """
    components = []
    if parameters:
        components.append({
            "type": "body",
            "parameters": [{"type": "text", "text": p} for p in parameters],
        })

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "template",
        "template": {
            "name": template_name,
            "language": {"code": language_code},
        },
    }
    if components:
        payload["template"]["components"] = components

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(_messages_url(), headers=_headers(), json=payload)
        response.raise_for_status()
        result = response.json()
        logger.info("Template message '%s' sent to %s", template_name, phone)
        return result


async def send_interactive_buttons(
    phone: str,
    body_text: str,
    buttons: List[Dict[str, str]],
    header_text: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Send an interactive message with reply buttons.

    Args:
        phone: Recipient phone number.
        body_text: Message body text.
        buttons: List of {'id': '...', 'title': '...'} dicts (max 3).
    """
    interactive = {
        "type": "button",
        "body": {"text": body_text},
        "action": {
            "buttons": [
                {"type": "reply", "reply": {"id": b["id"], "title": b["title"]}}
                for b in buttons[:3]
            ]
        },
    }
    if header_text:
        interactive["header"] = {"type": "text", "text": header_text}

    payload = {
        "messaging_product": "whatsapp",
        "to": phone,
        "type": "interactive",
        "interactive": interactive,
    }

    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(_messages_url(), headers=_headers(), json=payload)
        response.raise_for_status()
        return response.json()


# ── Downloading Media ────────────────────────────────────────


async def download_media(media_id: str) -> tuple[bytes, str]:
    """
    Download a media file sent by a user.

    Returns:
        Tuple of (file_bytes, mime_type).
    """
    settings = get_settings()
    headers = {"Authorization": f"Bearer {settings.meta_access_token}"}

    async with httpx.AsyncClient(timeout=60) as client:
        # Step 1: Get the media URL
        media_url_response = await client.get(
            f"{BASE_URL}/{media_id}", headers=headers
        )
        media_url_response.raise_for_status()
        media_info = media_url_response.json()
        download_url = media_info["url"]
        mime_type = media_info.get("mime_type", "application/octet-stream")

        # Step 2: Download the actual file
        file_response = await client.get(download_url, headers=headers)
        file_response.raise_for_status()

        logger.info("Downloaded media %s (%s, %d bytes)", media_id, mime_type, len(file_response.content))
        return file_response.content, mime_type


# ── Read Receipts ────────────────────────────────────────────


async def mark_as_read(message_id: str) -> None:
    """Mark a received message as read."""
    payload = {
        "messaging_product": "whatsapp",
        "status": "read",
        "message_id": message_id,
    }

    async with httpx.AsyncClient(timeout=10) as client:
        await client.post(_messages_url(), headers=_headers(), json=payload)


# ── Webhook Signature Verification ───────────────────────────


def verify_webhook_signature(payload_body: bytes, signature_header: str) -> bool:
    """
    Verify the X-Hub-Signature-256 header from Meta.

    Args:
        payload_body: Raw request body bytes.
        signature_header: Value of X-Hub-Signature-256 header.

    Returns:
        True if the signature is valid.
    """
    settings = get_settings()

    if not signature_header:
        return False

    # Header format: "sha256=<hex_digest>"
    expected_signature = "sha256=" + hmac.new(
        settings.meta_app_secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()

    return hmac.compare_digest(expected_signature, signature_header)


# ── Message Parsing Helpers ──────────────────────────────────


def extract_message_data(webhook_body: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """
    Extract the first message from a webhook payload.

    Returns dict with keys: phone, message_id, type, text, media_id, mime_type, button_id
    or None if no message found.
    """
    try:
        entry = webhook_body.get("entry", [])
        if not entry:
            return None

        changes = entry[0].get("changes", [])
        if not changes:
            return None

        value = changes[0].get("value", {})
        messages = value.get("messages", [])
        if not messages:
            return None

        msg = messages[0]
        phone = msg.get("from", "")
        message_id = msg.get("id", "")
        msg_type = msg.get("type", "")

        result = {
            "phone": phone,
            "message_id": message_id,
            "type": msg_type,
            "text": None,
            "media_id": None,
            "mime_type": None,
            "button_id": None,
        }

        if msg_type == "text":
            result["text"] = msg.get("text", {}).get("body", "")
        elif msg_type in ("image", "document"):
            media = msg.get(msg_type, {})
            result["media_id"] = media.get("id")
            result["mime_type"] = media.get("mime_type", "application/octet-stream")
        elif msg_type == "interactive":
            interactive = msg.get("interactive", {})
            if interactive.get("type") == "button_reply":
                result["button_id"] = interactive.get("button_reply", {}).get("id")

        return result

    except (IndexError, KeyError, TypeError) as e:
        logger.error("Failed to parse webhook payload: %s", e)
        return None
