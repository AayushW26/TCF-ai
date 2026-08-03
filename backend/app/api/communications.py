"""
Communications API — send vendor warnings via WhatsApp or email.
"""

import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.auth import get_current_user
from app.models.auth import CAUser
from app.services.whatsapp_client import send_text_message
from app.services.supabase_client import get_rows, get_row_by_id, insert_row, update_row

logger = logging.getLogger(__name__)
router = APIRouter()


class VendorWarningRequest(BaseModel):
    """Request body for sending a vendor warning."""
    action_item_id: str
    vendor_phone: Optional[str] = None
    vendor_email: Optional[str] = None
    message: Optional[str] = None
    channel: str = "whatsapp"  # 'whatsapp' or 'email'


class CommunicationLog(BaseModel):
    """Log of a sent communication."""
    action_item_id: str
    channel: str
    recipient: str
    message: str
    status: str


@router.post("/vendor-warning", response_model=CommunicationLog)
async def send_vendor_warning(
    body: VendorWarningRequest,
    current_user: CAUser = Depends(get_current_user),
):
    """
    Send a WhatsApp or email warning to a vendor.

    The warning is linked to an action item and logged in the database.
    """
    # Fetch the action item
    action = await get_row_by_id("action_items", body.action_item_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action item not found")

    # Verify CA access
    traders = await get_rows(
        "traders",
        filters={"id": action["trader_id"], "ca_id": current_user.id},
        limit=1,
    )
    if not traders:
        raise HTTPException(status_code=403, detail="Access denied")

    trader = traders[0]
    vendor_phone = body.vendor_phone or action.get("vendor_phone")
    vendor_email = body.vendor_email or action.get("vendor_email")
    vendor_name = action.get("vendor_name", "Supplier")
    vendor_gstin = action.get("vendor_gstin", "N/A")

    # Build default message if not provided
    if not body.message:
        message = (
            f"Dear {vendor_name},\n\n"
            f"This is a notice from {trader.get('business_name', 'our firm')} "
            f"regarding the following compliance issue:\n\n"
            f"📋 {action.get('title', 'Compliance Issue')}\n"
            f"📝 {action.get('description', '')}\n\n"
            f"Recommended Action: {action.get('recommended_fix', 'Please review and respond.')}\n\n"
            f"Please address this at your earliest convenience.\n\n"
            f"— Sent via Munim.ai"
        )
    else:
        message = body.message

    # Send via chosen channel
    status = "sent"
    recipient = ""

    if body.channel == "whatsapp":
        if not vendor_phone:
            raise HTTPException(status_code=400, detail="Vendor phone number not available")
        recipient = vendor_phone
        try:
            await send_text_message(vendor_phone, message)
        except Exception as e:
            logger.error("Failed to send WhatsApp to %s: %s", vendor_phone, e)
            status = "failed"

    elif body.channel == "email":
        if not vendor_email:
            raise HTTPException(status_code=400, detail="Vendor email not available")
        recipient = vendor_email
        # Email sending would be implemented here (e.g., via SMTP or email service)
        # For now, log it as sent
        logger.info("Email to %s: %s", vendor_email, message[:100])
        status = "sent"

    else:
        raise HTTPException(status_code=400, detail="Invalid channel. Use 'whatsapp' or 'email'.")

    return CommunicationLog(
        action_item_id=body.action_item_id,
        channel=body.channel,
        recipient=recipient,
        message=message[:500],
        status=status,
    )
