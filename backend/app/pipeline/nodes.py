"""
LangGraph pipeline nodes — six processing steps for invoice ingestion.

1. extract_invoice_node  — Gemini Vision OCR → InvoiceExtraction
2. validate_gstin_node   — DeepVue API → GSTIN validation
3. validate_hsn_node     — HSN code format & reference validation
4. apply_itc_rules_node  — ITC §16/§17(5) rules engine
5. score_fraud_node      — 6-signal fraud scoring
6. save_results_node     — Persist to Supabase + create action items
"""

import logging
from datetime import datetime

from app.pipeline.state import InvoicePipelineState
from app.services.gemini_client import extract_invoice
from app.services.deepvue_client import validate_gstin
from app.services.supabase_client import (
    insert_row,
    get_rows,
    update_row,
    upsert_row,
)
from app.domain.hsn import validate_hsn_list
from app.domain.itc_engine import classify_invoice
from app.domain.fraud import score_fraud
from app.domain.supplier_monitor import update_supplier_stats
from app.models.action import ActionType, ActionSeverity

logger = logging.getLogger(__name__)


# ── Node 1: Extract Invoice ─────────────────────────────────


async def extract_invoice_node(state: InvoicePipelineState) -> dict:
    """Run Gemini Vision OCR on the invoice image."""
    try:
        extraction = await extract_invoice(
            state["image_bytes"],
            state.get("mime_type", "image/jpeg"),
        )
        logger.info("Extraction complete: invoice=%s, confidence=%.2f",
                     extraction.invoice_number, extraction.confidence_score)
        return {"extraction": extraction}

    except Exception as e:
        logger.error("Extraction failed: %s", e)
        return {
            "extraction": None,
            "errors": state.get("errors", []) + [f"Extraction failed: {str(e)}"],
        }


# ── Node 2: Validate GSTIN ──────────────────────────────────


async def validate_gstin_node(state: InvoicePipelineState) -> dict:
    """Validate the supplier's GSTIN via DeepVue API."""
    extraction = state.get("extraction")
    if not extraction or not extraction.supplier_gstin:
        return {"gstin_info": None}

    try:
        gstin_info = await validate_gstin(extraction.supplier_gstin)
        logger.info("GSTIN %s validated: %s (active=%s)",
                     extraction.supplier_gstin, gstin_info.legal_name, gstin_info.is_active)
        return {"gstin_info": gstin_info}

    except Exception as e:
        logger.error("GSTIN validation failed: %s", e)
        return {
            "gstin_info": None,
            "errors": state.get("errors", []) + [f"GSTIN validation failed: {str(e)}"],
        }


# ── Node 3: Validate HSN Codes ──────────────────────────────


async def validate_hsn_node(state: InvoicePipelineState) -> dict:
    """Validate all HSN codes from the extracted line items."""
    extraction = state.get("extraction")
    if not extraction or not extraction.line_items:
        return {"hsn_results": []}

    hsn_codes = [item.hsn_code for item in extraction.line_items if item.hsn_code]
    results = validate_hsn_list(hsn_codes)

    valid_count = sum(1 for r in results if r.is_valid)
    logger.info("HSN validation: %d/%d codes valid", valid_count, len(results))

    return {"hsn_results": results}


# ── Node 4: ITC Rules Engine ────────────────────────────────


async def apply_itc_rules_node(state: InvoicePipelineState) -> dict:
    """Apply GST §16/§17(5) ITC eligibility rules."""
    extraction = state.get("extraction")
    if not extraction:
        return {"itc_result": None}

    gstin_info = state.get("gstin_info")
    fraud_result = state.get("fraud_result")

    itc_result = classify_invoice(
        extraction=extraction,
        gstin_is_active=gstin_info.is_active if gstin_info else True,
        gstin_days_since_registration=gstin_info.days_since_registration if gstin_info else None,
        is_in_gstr2b=False,  # Will be updated after reconciliation
        fraud_score=fraud_result.total_score if fraud_result else 0,
    )

    logger.info("ITC classification: %s (amount=₹%.2f)",
                 itc_result.status.value, itc_result.affected_amount)

    return {"itc_result": itc_result}


# ── Node 5: Fraud Scoring ───────────────────────────────────


async def score_fraud_node(state: InvoicePipelineState) -> dict:
    """Run the 6-signal fraud scoring engine."""
    extraction = state.get("extraction")
    if not extraction:
        return {"fraud_result": None}

    gstin_info = state.get("gstin_info")
    trader_state = state.get("trader_state_code")
    history = state.get("supplier_history", {})

    # Fetch supplier history from DB for fraud signals
    historical_amounts = []
    historical_invoice_numbers = []
    supplier_avg = None

    if extraction.supplier_gstin:
        try:
            past_invoices = await get_rows(
                "invoices",
                filters={
                    "supplier_gstin": extraction.supplier_gstin,
                    "trader_id": state["trader_id"],
                },
                select="total_amount,invoice_number",
                order_by="created_at.desc",
                limit=50,
            )
            historical_amounts = [
                inv["total_amount"] for inv in past_invoices
                if inv.get("total_amount") is not None
            ]
            historical_invoice_numbers = [
                inv["invoice_number"] for inv in past_invoices
                if inv.get("invoice_number")
            ]
            if historical_amounts:
                supplier_avg = sum(historical_amounts) / len(historical_amounts)
        except Exception as e:
            logger.warning("Could not fetch supplier history: %s", e)

    fraud_result = score_fraud(
        extraction=extraction,
        gstin_info=gstin_info,
        buyer_state_code=trader_state,
        historical_amounts=historical_amounts,
        historical_invoice_numbers=historical_invoice_numbers,
        supplier_average_amount=supplier_avg,
    )

    logger.info("Fraud score: %d/100 (flagged=%s)", fraud_result.total_score, fraud_result.is_flagged)

    return {"fraud_result": fraud_result}


# ── Node 6: Save Results ────────────────────────────────────


async def save_results_node(state: InvoicePipelineState) -> dict:
    """Persist the complete results to Supabase and create action items."""
    extraction = state.get("extraction")
    itc_result = state.get("itc_result")
    fraud_result = state.get("fraud_result")
    trader_id = state["trader_id"]
    action_count = 0

    if not extraction:
        logger.warning("No extraction data to save")
        return {"invoice_id": None, "action_items_created": 0}

    try:
        # Determine the period from the invoice date
        period = None
        if extraction.invoice_date:
            try:
                inv_date = datetime.strptime(extraction.invoice_date, "%Y-%m-%d")
                period = inv_date.strftime("%Y-%m")
            except ValueError:
                pass

        # Save invoice record
        invoice_data = {
            "trader_id": trader_id,
            "supplier_name": extraction.supplier_name,
            "supplier_gstin": extraction.supplier_gstin,
            "invoice_number": extraction.invoice_number,
            "invoice_date": extraction.invoice_date,
            "total_taxable_value": extraction.total_taxable_value,
            "cgst": extraction.cgst or 0,
            "sgst": extraction.sgst or 0,
            "igst": extraction.igst or 0,
            "cess": extraction.cess or 0,
            "total_amount": extraction.total_amount,
            "place_of_supply": extraction.place_of_supply,
            "reverse_charge": extraction.reverse_charge,
            "itc_status": itc_result.status.value if itc_result else "PENDING",
            "itc_blocked_reason": itc_result.blocked_reason if itc_result else None,
            "itc_blocked_section": itc_result.blocked_section if itc_result else None,
            "fraud_score": fraud_result.total_score if fraud_result else 0,
            "fraud_signals": [s for s in (fraud_result.signals if fraud_result else [])],
            "extraction_confidence": extraction.confidence_score,
            "source": state.get("source", "whatsapp"),
            "period": period,
        }

        saved_invoice = await insert_row("invoices", invoice_data)
        invoice_id = saved_invoice.get("id")

        # Save line items
        if extraction.line_items and invoice_id:
            line_items_data = [
                {
                    "invoice_id": invoice_id,
                    "description": item.description,
                    "hsn_code": item.hsn_code,
                    "quantity": item.quantity,
                    "rate": item.rate,
                    "taxable_value": item.taxable_value,
                    "cgst_rate": item.cgst_rate or 0,
                    "sgst_rate": item.sgst_rate or 0,
                    "igst_rate": item.igst_rate or 0,
                    "cgst": item.cgst or 0,
                    "sgst": item.sgst or 0,
                    "igst": item.igst or 0,
                    "cess": item.cess or 0,
                }
                for item in extraction.line_items
            ]
            from app.services.supabase_client import insert_rows
            await insert_rows("invoice_line_items", line_items_data)

        # Create action items based on ITC status
        if itc_result and itc_result.status != "CONFIRMED" and invoice_id:
            severity_map = {
                "FRAUD_FLAGGED": ActionSeverity.CRITICAL,
                "AT_RISK": ActionSeverity.HIGH,
                "INELIGIBLE": ActionSeverity.MEDIUM,
                "FIXABLE_BLOCKED": ActionSeverity.MEDIUM,
            }
            type_map = {
                "FRAUD_FLAGGED": ActionType.FRAUD_FLAG,
                "AT_RISK": ActionType.ITC_AT_RISK,
                "INELIGIBLE": ActionType.FIXABLE_BLOCK,
                "FIXABLE_BLOCKED": ActionType.FIXABLE_BLOCK,
            }

            status_val = itc_result.status.value
            total_tax = itc_result.affected_amount

            action_data = {
                "trader_id": trader_id,
                "invoice_id": invoice_id,
                "action_type": type_map.get(status_val, ActionType.FIXABLE_BLOCK).value,
                "severity": severity_map.get(status_val, ActionSeverity.MEDIUM).value,
                "title": f"ITC {status_val.replace('_', ' ').title()}: {extraction.supplier_name or 'Unknown'}",
                "description": itc_result.blocked_reason or "ITC issue detected",
                "affected_amount": total_tax,
                "recommended_fix": itc_result.fix_suggestion,
                "vendor_gstin": extraction.supplier_gstin,
                "vendor_name": extraction.supplier_name,
            }
            await insert_row("action_items", action_data)
            action_count += 1

        # Update/create supplier profile
        if extraction.supplier_gstin:
            gstin_info = state.get("gstin_info")
            supplier_data = {
                "trader_id": trader_id,
                "supplier_gstin": extraction.supplier_gstin,
                "supplier_name": extraction.supplier_name or (gstin_info.legal_name if gstin_info else None),
                "trade_name": gstin_info.trade_name if gstin_info else None,
                "registration_date": gstin_info.registration_date if gstin_info else None,
                "business_type": gstin_info.business_type if gstin_info else None,
                "state_code": gstin_info.state_code if gstin_info else None,
            }

            # Check if supplier profile exists
            existing = await get_rows(
                "supplier_profiles",
                filters={
                    "trader_id": trader_id,
                    "supplier_gstin": extraction.supplier_gstin,
                },
                limit=1,
            )

            if existing:
                profile = update_supplier_stats(existing[0], extraction.total_amount or 0)
                profile["last_invoice_date"] = extraction.invoice_date
                await update_row("supplier_profiles", existing[0]["id"], profile)
            else:
                supplier_data.update({
                    "total_invoice_count": 1,
                    "total_invoice_value": extraction.total_amount or 0,
                    "average_invoice_value": extraction.total_amount or 0,
                    "last_invoice_date": extraction.invoice_date,
                })
                await insert_row("supplier_profiles", supplier_data)

        logger.info("Results saved: invoice_id=%s, actions=%d", invoice_id, action_count)
        return {"invoice_id": invoice_id, "action_items_created": action_count}

    except Exception as e:
        logger.error("Failed to save results: %s", e)
        return {
            "invoice_id": None,
            "action_items_created": 0,
            "errors": state.get("errors", []) + [f"Save failed: {str(e)}"],
        }
