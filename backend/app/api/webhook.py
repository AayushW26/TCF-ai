"""
WhatsApp Webhook API — Meta verification, message handling, and invoice ingestion.

Handles:
  GET  /api/v1/webhook          — Meta verification handshake
  POST /api/v1/webhook          — Incoming WhatsApp messages
  POST /api/v1/webhook/upload-invoice — Direct upload from Trader PWA
"""

import logging
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Query, Request, HTTPException, UploadFile, File, Form

from app.config import get_settings
from app.services.whatsapp_client import (
    verify_webhook_signature,
    extract_message_data,
    send_text_message,
    send_interactive_buttons,
    download_media,
    mark_as_read,
)
from app.services.redis_client import get_conversation_state, set_conversation_state
from app.services.supabase_client import get_rows, insert_row, update_row
from app.services.deepvue_client import validate_gstin
from app.pipeline.graph import process_invoice

logger = logging.getLogger(__name__)
router = APIRouter()


# ── WhatsApp Verification Handshake ──────────────────────────


@router.get("")
async def verify_webhook(
    hub_mode: str = Query(None, alias="hub.mode"),
    hub_verify_token: str = Query(None, alias="hub.verify_token"),
    hub_challenge: str = Query(None, alias="hub.challenge"),
):
    """Meta webhook verification — returns the challenge if token matches."""
    settings = get_settings()

    if hub_mode == "subscribe" and hub_verify_token == settings.whatsapp_verify_token:
        logger.info("WhatsApp webhook verified")
        return int(hub_challenge)

    raise HTTPException(status_code=403, detail="Verification failed")


# ── Incoming WhatsApp Messages ───────────────────────────────


@router.post("")
async def handle_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    Handle incoming WhatsApp messages.

    Returns 200 immediately; processes messages in background tasks.
    """
    body_bytes = await request.body()
    body = await request.json()

    # Verify signature (optional in dev, required in production)
    settings = get_settings()
    signature = request.headers.get("X-Hub-Signature-256", "")
    if settings.is_production and not verify_webhook_signature(body_bytes, signature):
        raise HTTPException(status_code=403, detail="Invalid signature")

    # Extract message data
    msg_data = extract_message_data(body)
    if not msg_data:
        return {"status": "ok"}  # Status update or other non-message event

    # Process in background
    background_tasks.add_task(_process_message, msg_data)

    return {"status": "ok"}


async def _process_message(msg_data: dict):
    """Process a single WhatsApp message (runs as background task)."""
    phone = msg_data["phone"]
    msg_type = msg_data["type"]
    message_id = msg_data["message_id"]

    try:
        # Mark as read
        await mark_as_read(message_id)

        if msg_type == "text":
            await _handle_text_message(phone, msg_data["text"])
        elif msg_type in ("image", "document"):
            await _handle_media_message(phone, msg_data["media_id"], msg_data["mime_type"])
        elif msg_type == "interactive" and msg_data.get("button_id"):
            await _handle_button_reply(phone, msg_data["button_id"])
        else:
            await send_text_message(
                phone,
                "🙏 Sorry, I can only process text messages, images, and documents. "
                "Please send a photo of your invoice or type 'help' for assistance."
            )

    except Exception as e:
        logger.error("Error processing message from %s: %s", phone, e)
        await send_text_message(
            phone,
            "⚠️ Something went wrong. Please try again or contact support."
        )


# ── Conversational Onboarding State Machine ──────────────────


async def _handle_text_message(phone: str, text: str):
    """Handle text messages — manage onboarding flow or route commands."""
    text_lower = text.strip().lower()

    # Check for commands
    if text_lower in ("help", "hi", "hello", "start"):
        await _send_welcome(phone)
        return

    if text_lower == "status":
        await _send_status(phone)
        return

    # Check conversation state
    conv_state = await get_conversation_state(phone)

    if not conv_state:
        # New user — start onboarding
        await _start_onboarding(phone)
        return

    state = conv_state.get("state", "INIT")

    if state == "INIT":
        await _start_onboarding(phone)
    elif state == "AWAITING_NAME":
        await _receive_business_name(phone, text)
    elif state == "AWAITING_GSTIN":
        await _receive_gstin(phone, text)
    elif state == "AWAITING_CONFIRMATION":
        await _handle_confirmation(phone, text)
    elif state == "ACTIVE":
        # Active trader — interpret as general message
        await send_text_message(
            phone,
            "📸 Send me a photo or PDF of your invoice and I'll extract the details!\n\n"
            "Or type:\n"
            "• *help* — see options\n"
            "• *status* — check your account"
        )
    else:
        await _start_onboarding(phone)


async def _send_welcome(phone: str):
    """Send welcome message."""
    await send_text_message(
        phone,
        "🙏 *Namaste! Welcome to Munim.ai*\n\n"
        "I'm your GST compliance assistant. I can:\n\n"
        "📸 Extract invoice data from photos\n"
        "✅ Check ITC eligibility\n"
        "🔍 Detect fraud signals\n"
        "📊 Reconcile with GSTR-2B\n\n"
        "To get started, send me your *business name*."
    )
    await set_conversation_state(phone, "AWAITING_NAME", {}, ttl=7200)


async def _start_onboarding(phone: str):
    """Start the onboarding flow for a new user."""
    await send_text_message(
        phone,
        "🙏 *Welcome to Munim.ai!*\n\n"
        "Let's set up your account. This takes under 2 minutes.\n\n"
        "Please send me your *business name*."
    )
    await set_conversation_state(phone, "AWAITING_NAME", {}, ttl=7200)


async def _receive_business_name(phone: str, name: str):
    """Step 2: Receive business name, ask for GSTIN."""
    await set_conversation_state(
        phone, "AWAITING_GSTIN",
        {"business_name": name.strip()},
        ttl=7200,
    )
    await send_text_message(
        phone,
        f"✅ Business name: *{name.strip()}*\n\n"
        "Now please send me your *15-digit GSTIN*.\n"
        "Example: `27AADCB2230M1ZP`\n\n"
        "If you don't have one yet, type *skip*."
    )


async def _receive_gstin(phone: str, gstin_text: str):
    """Step 3: Receive GSTIN, validate, and ask for confirmation."""
    conv_state = await get_conversation_state(phone)
    context = conv_state.get("context", {}) if conv_state else {}
    business_name = context.get("business_name", "")

    gstin = gstin_text.strip().upper()

    if gstin == "SKIP":
        context["gstin"] = None
        await set_conversation_state(phone, "AWAITING_CONFIRMATION", context, ttl=7200)
        await send_interactive_buttons(
            phone,
            f"📋 *Confirm your details:*\n\n"
            f"Business: {business_name}\n"
            f"GSTIN: Not provided\n\n"
            f"Is this correct?",
            [
                {"id": "confirm_yes", "title": "✅ Yes, confirm"},
                {"id": "confirm_no", "title": "❌ No, restart"},
            ],
        )
        return

    # Validate GSTIN format
    if len(gstin) != 15:
        await send_text_message(
            phone,
            "❌ GSTIN must be exactly 15 characters.\n"
            "Please re-enter your GSTIN or type *skip*."
        )
        return

    # Validate via DeepVue
    gstin_info = await validate_gstin(gstin)

    if gstin_info.is_valid:
        context["gstin"] = gstin
        context["gstin_info"] = {
            "legal_name": gstin_info.legal_name,
            "trade_name": gstin_info.trade_name,
            "status": gstin_info.status,
            "state_code": gstin_info.state_code,
        }
        await set_conversation_state(phone, "AWAITING_CONFIRMATION", context, ttl=7200)

        await send_interactive_buttons(
            phone,
            f"📋 *Confirm your details:*\n\n"
            f"Business: {business_name}\n"
            f"GSTIN: {gstin}\n"
            f"Legal Name: {gstin_info.legal_name or 'N/A'}\n"
            f"Status: {gstin_info.status or 'N/A'}\n\n"
            f"Is this correct?",
            [
                {"id": "confirm_yes", "title": "✅ Yes, confirm"},
                {"id": "confirm_no", "title": "❌ No, restart"},
            ],
        )
    else:
        await send_text_message(
            phone,
            f"⚠️ Could not validate GSTIN: {gstin}\n"
            "Please check and re-enter, or type *skip*."
        )


async def _handle_button_reply(phone: str, button_id: str):
    """Handle interactive button replies."""
    if button_id == "confirm_yes":
        await _handle_confirmation(phone, "yes")
    elif button_id == "confirm_no":
        await _start_onboarding(phone)


async def _handle_confirmation(phone: str, text: str):
    """Step 4: Confirmation — create the trader record."""
    text_lower = text.strip().lower()

    if text_lower in ("no", "n", "restart"):
        await _start_onboarding(phone)
        return

    if text_lower not in ("yes", "y", "confirm", "ok"):
        await send_text_message(phone, "Please reply *yes* or *no*.")
        return

    conv_state = await get_conversation_state(phone)
    context = conv_state.get("context", {}) if conv_state else {}

    # Find or create trader — link to first available CA for now
    # (In production, this would use an invitation/linking system)
    ca_users = await get_rows("ca_users", limit=1)
    if not ca_users:
        await send_text_message(
            phone,
            "⚠️ No CA accounts found. Please ask your CA to register on the dashboard first."
        )
        return

    ca_id = ca_users[0]["id"]
    gstin_info = context.get("gstin_info", {})

    trader_data = {
        "ca_id": ca_id,
        "business_name": context.get("business_name", "Unknown"),
        "gstin": context.get("gstin"),
        "phone": phone,
        "state_code": gstin_info.get("state_code"),
        "onboarding_state": "ACTIVE",
    }

    created_trader = await insert_row("traders", trader_data)

    # Update conversation state
    await set_conversation_state(
        phone, "ACTIVE",
        {"trader_id": created_trader["id"]},
        ttl=86400,
    )

    # Save conversation to DB for persistence
    await insert_row("conversations", {
        "phone": phone,
        "trader_id": created_trader["id"],
        "current_state": "ACTIVE",
        "context": {"trader_id": created_trader["id"]},
    })

    await send_text_message(
        phone,
        "🎉 *Account created successfully!*\n\n"
        "You're all set. Now you can:\n\n"
        "📸 Send a photo of any invoice\n"
        "📄 Forward a PDF invoice\n\n"
        "I'll automatically extract the data, check ITC eligibility, "
        "and flag any issues for your CA.\n\n"
        "Try it now — send me an invoice!"
    )


# ── Media Message Handling ───────────────────────────────────


async def _handle_media_message(phone: str, media_id: str, mime_type: str):
    """Handle image/document messages — download and process through pipeline."""
    # Find trader by phone
    conv_state = await get_conversation_state(phone)
    trader_id = None

    if conv_state and conv_state.get("context", {}).get("trader_id"):
        trader_id = conv_state["context"]["trader_id"]
    else:
        # Check DB
        conversations = await get_rows("conversations", filters={"phone": phone}, limit=1)
        if conversations:
            trader_id = conversations[0].get("trader_id")
            # Refresh Redis cache
            await set_conversation_state(
                phone, "ACTIVE",
                {"trader_id": trader_id},
                ttl=86400,
            )

    if not trader_id:
        await send_text_message(
            phone,
            "⚠️ Please complete onboarding first. Type *start* to begin."
        )
        return

    # Acknowledge receipt
    await send_text_message(phone, "📥 Invoice received! Processing... ⏳")

    try:
        # Download media
        image_bytes, actual_mime = await download_media(media_id)

        # Get trader state code
        traders = await get_rows("traders", filters={"id": trader_id}, limit=1)
        trader_state = traders[0].get("state_code") if traders else None

        # Process through pipeline
        result = await process_invoice(
            image_bytes=image_bytes,
            trader_id=trader_id,
            mime_type=actual_mime,
            source="whatsapp",
            trader_state_code=trader_state,
        )

        # Send result summary
        await _send_extraction_summary(phone, result)

    except Exception as e:
        logger.error("Failed to process invoice from %s: %s", phone, e)
        await send_text_message(
            phone,
            "❌ Failed to process the invoice. Please try again with a clearer image."
        )


async def _send_extraction_summary(phone: str, result: dict):
    """Send a WhatsApp summary of the extraction results."""
    extraction = result.get("extraction")
    itc_result = result.get("itc_result")
    fraud_result = result.get("fraud_result")

    if not extraction:
        await send_text_message(phone, "❌ Could not extract invoice data. Please send a clearer image.")
        return

    # Build summary message
    lines = ["📋 *Invoice Extracted Successfully!*\n"]

    if extraction.supplier_name:
        lines.append(f"🏢 Supplier: *{extraction.supplier_name}*")
    if extraction.supplier_gstin:
        lines.append(f"🆔 GSTIN: `{extraction.supplier_gstin}`")
    if extraction.invoice_number:
        lines.append(f"📄 Invoice #: {extraction.invoice_number}")
    if extraction.invoice_date:
        lines.append(f"📅 Date: {extraction.invoice_date}")
    if extraction.total_amount:
        lines.append(f"💰 Amount: ₹{extraction.total_amount:,.2f}")

    # Tax breakdown
    total_tax = (extraction.cgst or 0) + (extraction.sgst or 0) + (extraction.igst or 0) + (extraction.cess or 0)
    if total_tax > 0:
        lines.append(f"🏛️ Tax: ₹{total_tax:,.2f}")

    lines.append("")

    # ITC Status
    if itc_result:
        status_emoji = {
            "CONFIRMED": "✅",
            "AT_RISK": "⚠️",
            "FIXABLE_BLOCKED": "🔧",
            "INELIGIBLE": "❌",
            "FRAUD_FLAGGED": "🚨",
            "PENDING": "⏳",
        }
        emoji = status_emoji.get(itc_result.status.value, "❓")
        lines.append(f"{emoji} *ITC Status: {itc_result.status.value.replace('_', ' ')}*")
        if itc_result.blocked_reason:
            lines.append(f"   Reason: {itc_result.blocked_reason[:200]}")
        if itc_result.fix_suggestion:
            lines.append(f"   💡 Fix: {itc_result.fix_suggestion[:200]}")

    # Fraud Score
    if fraud_result and fraud_result.total_score > 0:
        lines.append(f"\n🔍 Fraud Score: {fraud_result.total_score}/100")
        if fraud_result.is_flagged:
            lines.append("🚨 *FRAUD ALERT — investigate this invoice*")
        elif fraud_result.is_soft_flag:
            lines.append("⚠️ Elevated risk — CA review recommended")

    # Confidence
    lines.append(f"\n📊 Extraction Confidence: {extraction.confidence_score:.0%}")

    await send_text_message(phone, "\n".join(lines))


async def _send_status(phone: str):
    """Send account status to the user."""
    conv_state = await get_conversation_state(phone)
    if not conv_state or not conv_state.get("context", {}).get("trader_id"):
        await send_text_message(phone, "You don't have an active account. Type *start* to begin onboarding.")
        return

    trader_id = conv_state["context"]["trader_id"]
    traders = await get_rows("traders", filters={"id": trader_id}, limit=1)

    if not traders:
        await send_text_message(phone, "Account not found. Type *start* to re-register.")
        return

    trader = traders[0]
    invoices = await get_rows("invoices", filters={"trader_id": trader_id})

    await send_text_message(
        phone,
        f"📊 *Account Status*\n\n"
        f"Business: {trader.get('business_name', 'N/A')}\n"
        f"GSTIN: {trader.get('gstin', 'Not set')}\n"
        f"Invoices processed: {len(invoices)}\n\n"
        f"📸 Send me an invoice photo to process!"
    )


# ── Direct Upload (Trader PWA) ───────────────────────────────


@router.post("/upload-invoice")
async def upload_invoice(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    trader_id: str = Form(...),
):
    """
    Direct invoice upload from the Trader PWA.

    Processes the file through the full pipeline in the background.
    """
    # Validate trader exists
    traders = await get_rows("traders", filters={"id": trader_id}, limit=1)
    if not traders:
        raise HTTPException(status_code=404, detail="Trader not found")

    # Read file
    contents = await file.read()
    mime_type = file.content_type or "application/octet-stream"

    # Process in background
    background_tasks.add_task(
        process_invoice,
        image_bytes=contents,
        trader_id=trader_id,
        mime_type=mime_type,
        source="upload",
        trader_state_code=traders[0].get("state_code"),
    )

    return {"status": "processing", "message": "Invoice uploaded and queued for processing"}
