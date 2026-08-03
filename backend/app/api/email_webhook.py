"""
Email Webhook API — Cloudmailin inbound email ingestion.

Receives forwarded vendor emails containing invoice PDFs,
identifies the trader by destination email, and processes
attachments through the invoice pipeline.
"""

import base64
import hashlib
import hmac
import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Request, HTTPException

from app.config import get_settings
from app.services.supabase_client import get_rows
from app.pipeline.graph import process_invoice

logger = logging.getLogger(__name__)
router = APIRouter()


def _verify_cloudmailin_signature(payload: dict, signature: str) -> bool:
    """Verify the Cloudmailin webhook signature."""
    settings = get_settings()
    # Cloudmailin uses basic auth or signature verification
    # This is a simplified check — adjust based on your Cloudmailin config
    if not signature or not settings.cloudmailin_secret:
        return False
    return hmac.compare_digest(signature, settings.cloudmailin_secret)


@router.post("")
async def handle_email_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Handle inbound emails from Cloudmailin.

    Cloudmailin sends a JSON payload with the email contents and attachments.
    We identify the trader by the destination email address and process
    all PDF/image attachments through the invoice pipeline.
    """
    body = await request.json()

    # Extract email metadata
    envelope = body.get("envelope", {})
    headers = body.get("headers", {})
    attachments = body.get("attachments", [])

    to_address = envelope.get("to", "")
    from_address = envelope.get("from", "")
    subject = headers.get("Subject", "No Subject")

    logger.info("Inbound email from %s to %s: %s", from_address, to_address, subject)

    # Find trader by munim_email
    traders = await get_rows("traders", filters={"munim_email": to_address}, limit=1)

    if not traders:
        # Try partial match (in case of +suffix or case differences)
        all_traders = await get_rows("traders")
        for t in all_traders:
            munim = t.get("munim_email", "")
            if munim and to_address.lower().startswith(munim.split("@")[0].lower()):
                traders = [t]
                break

    if not traders:
        logger.warning("No trader found for email address: %s", to_address)
        return {"status": "ignored", "reason": "Unknown recipient email"}

    trader = traders[0]
    trader_id = trader["id"]
    trader_state = trader.get("state_code")

    # Process attachments
    processed = 0

    for attachment in attachments:
        content_type = attachment.get("content_type", "")
        file_name = attachment.get("file_name", "")
        content = attachment.get("content", "")

        # Only process PDFs and images
        supported_types = [
            "application/pdf",
            "image/jpeg", "image/jpg",
            "image/png",
            "image/tiff",
        ]

        if not any(content_type.startswith(t) for t in supported_types):
            logger.debug("Skipping unsupported attachment: %s (%s)", file_name, content_type)
            continue

        try:
            # Decode base64 content
            file_bytes = base64.b64decode(content)

            # Process in background
            background_tasks.add_task(
                process_invoice,
                image_bytes=file_bytes,
                trader_id=trader_id,
                mime_type=content_type,
                source="email",
                trader_state_code=trader_state,
            )
            processed += 1
            logger.info("Queued email attachment for processing: %s (%s)", file_name, content_type)

        except Exception as e:
            logger.error("Failed to process attachment %s: %s", file_name, e)

    # Process inline/embedded images from email body if no attachments
    if processed == 0:
        plain_body = body.get("plain", body.get("body", {}).get("plain", ""))
        html_body = body.get("html", body.get("body", {}).get("html", ""))

        if not plain_body and not html_body and not attachments:
            logger.info("Email from %s has no processable content", from_address)
            return {"status": "ignored", "reason": "No attachments or content to process"}

    return {
        "status": "processing",
        "attachments_queued": processed,
        "trader_id": trader_id,
    }
