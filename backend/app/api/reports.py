"""
Reports API — PDF compliance report generation.

Uses Jinja2 HTML templates rendered to PDF via WeasyPrint.
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.api.auth import get_current_user
from app.models.auth import CAUser
from app.services.supabase_client import get_rows, insert_row

logger = logging.getLogger(__name__)
router = APIRouter()

# Template directory
TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


async def _verify_trader(trader_id: str, ca_id: str):
    """Verify CA owns this trader."""
    traders = await get_rows("traders", filters={"id": trader_id, "ca_id": ca_id}, limit=1)
    if not traders:
        raise HTTPException(status_code=404, detail="Trader not found")
    return traders[0]


def _build_report_html(
    trader: dict,
    invoices: list,
    actions: list,
    suppliers: list,
    period: str,
) -> str:
    """Build the compliance report HTML from a Jinja2 template."""
    from jinja2 import Environment, FileSystemLoader

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)))
    template = env.get_template("compliance_report.html")

    # Calculate summaries
    total_itc = 0
    confirmed = 0
    at_risk = 0
    blocked = 0
    fraud_flagged = 0

    for inv in invoices:
        tax = sum([
            inv.get("cgst", 0) or 0,
            inv.get("sgst", 0) or 0,
            inv.get("igst", 0) or 0,
            inv.get("cess", 0) or 0,
        ])
        total_itc += tax
        status = inv.get("itc_status", "PENDING")
        if status == "CONFIRMED":
            confirmed += tax
        elif status == "AT_RISK":
            at_risk += tax
        elif status in ("FIXABLE_BLOCKED", "INELIGIBLE"):
            blocked += tax
        elif status == "FRAUD_FLAGGED":
            fraud_flagged += tax

    matched = sum(1 for inv in invoices if inv.get("reconciliation_status") != "UNMATCHED")
    unmatched = len(invoices) - matched

    flagged_suppliers = [s for s in suppliers if s.get("is_flagged")]

    html = template.render(
        trader=trader,
        period=period,
        generated_at=datetime.now().strftime("%d %B %Y, %I:%M %p"),
        total_invoices=len(invoices),
        total_itc=total_itc,
        confirmed=confirmed,
        at_risk=at_risk,
        blocked=blocked,
        fraud_flagged=fraud_flagged,
        invoices=invoices[:50],  # Limit to 50 for PDF size
        actions=[a for a in actions if not a.get("is_resolved")][:20],
        matched_count=matched,
        unmatched_count=unmatched,
        total_suppliers=len(suppliers),
        flagged_suppliers=flagged_suppliers,
    )
    return html


def _html_to_pdf(html: str) -> bytes:
    """Convert HTML to PDF using WeasyPrint."""
    from weasyprint import HTML
    return HTML(string=html).write_pdf()


@router.post("/generate/{trader_id}")
async def generate_report(
    trader_id: str,
    period: str = None,
    current_user: CAUser = Depends(get_current_user),
):
    """
    Generate a compliance PDF report for a trader.

    Returns the PDF directly as a download.
    """
    trader = await _verify_trader(trader_id, current_user.id)

    # Determine period
    if not period:
        period = datetime.now().strftime("%Y-%m")

    # Fetch data
    filters = {"trader_id": trader_id}
    invoices = await get_rows("invoices", filters=filters, order_by="created_at.desc")
    actions = await get_rows("action_items", filters=filters, order_by="created_at.desc")
    suppliers = await get_rows("supplier_profiles", filters=filters, order_by="compliance_score")

    # Build HTML
    html = _build_report_html(trader, invoices, actions, suppliers, period)

    # Generate PDF
    try:
        pdf_bytes = _html_to_pdf(html)
    except Exception as e:
        logger.error("PDF generation failed: %s", e)
        raise HTTPException(status_code=500, detail="PDF generation failed")

    # Save report metadata
    report_data = {
        "trader_id": trader_id,
        "ca_id": current_user.id,
        "period": period,
        "report_type": "compliance",
    }
    await insert_row("reports", report_data)

    filename = f"compliance_report_{trader.get('business_name', 'trader')}_{period}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/{trader_id}")
async def list_reports(
    trader_id: str,
    current_user: CAUser = Depends(get_current_user),
):
    """List past reports for a trader."""
    await _verify_trader(trader_id, current_user.id)

    reports = await get_rows(
        "reports",
        filters={"trader_id": trader_id},
        order_by="generated_at.desc",
    )
    return reports
