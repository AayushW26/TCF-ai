"""
GSTR-2B API — file upload, parsing, and reconciliation.
"""

import json
import logging
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File

from app.api.auth import get_current_user
from app.models.auth import CAUser
from app.models.gstr2b import (
    GSTR2BRecord,
    GSTR2BUploadResponse,
    ReconciliationResult,
    ReconciliationSummary,
)
from app.services.supabase_client import get_rows, insert_row, insert_rows, update_row
from app.domain.reconciler import reconcile

logger = logging.getLogger(__name__)
router = APIRouter()


async def _verify_trader(trader_id: str, ca_id: str):
    """Verify CA owns this trader."""
    traders = await get_rows("traders", filters={"id": trader_id, "ca_id": ca_id}, limit=1)
    if not traders:
        raise HTTPException(status_code=404, detail="Trader not found")
    return traders[0]


def _parse_gstr2b_json(data: dict, trader_id: str) -> tuple[List[dict], str, List[str]]:
    """
    Parse a GSTR-2B JSON file into a list of record dicts.

    Handles the standard GST portal GSTR-2B JSON format.

    Returns:
        Tuple of (records, period, errors).
    """
    records = []
    errors = []

    # Try to extract period from the header
    period = ""
    header = data.get("data", data)

    # Try different format structures
    if "docdata" in header:
        # Newer format
        doc = header["docdata"]
        period = header.get("rtnprd", "")
    elif "data" in header and isinstance(header["data"], dict):
        doc = header["data"].get("docdata", header["data"])
        period = header.get("data", {}).get("rtnprd", "")
    else:
        doc = header
        period = data.get("rtnprd", data.get("fp", ""))

    # Convert period format: "082026" → "2026-08" or keep if already YYYY-MM
    if period and len(period) == 6 and period.isdigit():
        period = f"{period[2:]}-{period[:2]}"

    # Parse B2B invoices
    b2b = doc.get("b2b", [])
    for supplier in b2b:
        supplier_gstin = supplier.get("ctin", "")
        supplier_name = supplier.get("trdnm", "")

        for invoice in supplier.get("inv", []):
            try:
                # Parse tax details
                itms = invoice.get("itms", [])
                igst = sum(item.get("itm_det", {}).get("iamt", 0) or 0 for item in itms)
                cgst = sum(item.get("itm_det", {}).get("camt", 0) or 0 for item in itms)
                sgst = sum(item.get("itm_det", {}).get("samt", 0) or 0 for item in itms)
                cess = sum(item.get("itm_det", {}).get("csamt", 0) or 0 for item in itms)
                taxable = sum(item.get("itm_det", {}).get("txval", 0) or 0 for item in itms)

                record = {
                    "trader_id": trader_id,
                    "period": period,
                    "supplier_gstin": supplier_gstin,
                    "supplier_name": supplier_name,
                    "invoice_number": invoice.get("inum", ""),
                    "invoice_date": _convert_date(invoice.get("idt", "")),
                    "invoice_value": invoice.get("val", 0),
                    "taxable_value": taxable,
                    "igst": igst,
                    "cgst": cgst,
                    "sgst": sgst,
                    "cess": cess,
                    "place_of_supply": invoice.get("pos", ""),
                    "reverse_charge": invoice.get("rchrg", "N") == "Y",
                    "itc_available": True,
                }
                records.append(record)

            except Exception as e:
                errors.append(f"Failed to parse invoice from {supplier_gstin}: {str(e)}")

    return records, period, errors


def _convert_date(date_str: str) -> Optional[str]:
    """Convert DD-MM-YYYY to YYYY-MM-DD."""
    if not date_str:
        return None
    try:
        parts = date_str.split("-")
        if len(parts) == 3:
            if len(parts[0]) == 4:
                return date_str  # Already YYYY-MM-DD
            return f"{parts[2]}-{parts[1]}-{parts[0]}"
    except Exception:
        pass
    return None


# ── Endpoints ────────────────────────────────────────────────


@router.post("/upload-file/{trader_id}", response_model=GSTR2BUploadResponse)
async def upload_gstr2b(
    trader_id: str,
    file: UploadFile = File(...),
    current_user: CAUser = Depends(get_current_user),
):
    """Upload a GSTR-2B JSON file and parse it into records."""
    await _verify_trader(trader_id, current_user.id)

    # Read and parse JSON
    try:
        contents = await file.read()
        data = json.loads(contents)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")

    # Parse records
    records, period, errors = _parse_gstr2b_json(data, trader_id)

    if not records:
        raise HTTPException(
            status_code=400,
            detail=f"No B2B invoice records found in the file. Errors: {'; '.join(errors)}"
        )

    # Store records
    stored = await insert_rows("gstr2b_records", records)

    return GSTR2BUploadResponse(
        records_parsed=len(records),
        records_stored=len(stored),
        period=period,
        errors=errors,
    )


@router.post("/reconcile/{trader_id}", response_model=ReconciliationSummary)
async def reconcile_gstr2b(
    trader_id: str,
    period: str = None,
    current_user: CAUser = Depends(get_current_user),
):
    """
    Trigger 3-pass reconciliation between invoices and GSTR-2B records.

    If period is not specified, uses the latest period available.
    """
    await _verify_trader(trader_id, current_user.id)

    # Determine period
    if not period:
        latest = await get_rows(
            "gstr2b_records",
            filters={"trader_id": trader_id},
            order_by="period.desc",
            limit=1,
        )
        if not latest:
            raise HTTPException(status_code=400, detail="No GSTR-2B records found. Upload a file first.")
        period = latest[0]["period"]

    # Fetch data
    invoices = await get_rows("invoices", filters={"trader_id": trader_id, "period": period})
    gstr2b_records = await get_rows("gstr2b_records", filters={"trader_id": trader_id, "period": period})

    if not gstr2b_records:
        raise HTTPException(status_code=400, detail=f"No GSTR-2B records for period {period}")

    # Run reconciliation
    results, summary, action_items = reconcile(invoices, gstr2b_records, trader_id, period)

    # Persist results
    for result in results:
        await insert_row("reconciliation_results", result.model_dump(exclude={"id"}))

        # Update invoice reconciliation status
        if result.invoice_id:
            await update_row("invoices", result.invoice_id, {
                "reconciliation_status": result.match_type.value,
                "matched_gstr2b_id": result.gstr2b_id,
            })

    # Persist action items
    for action in action_items:
        await insert_row("action_items", action.model_dump(exclude={"id", "created_at", "resolved_at"}))

    return summary


@router.get("/records/{trader_id}", response_model=List[GSTR2BRecord])
async def get_gstr2b_records(
    trader_id: str,
    period: str = None,
    current_user: CAUser = Depends(get_current_user),
):
    """Fetch GSTR-2B records with optional period filter."""
    await _verify_trader(trader_id, current_user.id)

    filters = {"trader_id": trader_id}
    if period:
        filters["period"] = period

    records = await get_rows(
        "gstr2b_records",
        filters=filters,
        order_by="uploaded_at.desc",
    )
    return [GSTR2BRecord(**r) for r in records]
