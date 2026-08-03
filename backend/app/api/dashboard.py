"""
CA Dashboard API — trader management, ITC summary, actions, suppliers, invoices.

All endpoints require JWT authentication.
"""

import logging
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.auth import get_current_user
from app.models.auth import CAUser
from app.models.trader import TraderCreate, TraderResponse, TraderBrief
from app.models.invoice import InvoiceRecord, InvoiceListResponse, ITCStatus
from app.models.action import ActionItem, ActionResolve, ActionListResponse, SEVERITY_ORDER
from app.models.dashboard import (
    ITCSummary,
    SupplierHealth,
    ITCTimelinePoint,
    ComplianceDeadline,
    DashboardSummary,
)
from app.services.supabase_client import (
    get_rows,
    get_row_by_id,
    insert_row,
    update_row,
    count_rows,
)
from app.config import get_settings

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Helpers ──────────────────────────────────────────────────


async def _verify_trader_access(trader_id: str, ca_id: str):
    """Verify the CA has access to this trader."""
    traders = await get_rows(
        "traders", filters={"id": trader_id, "ca_id": ca_id}, limit=1
    )
    if not traders:
        raise HTTPException(status_code=404, detail="Trader not found")
    return traders[0]


# ── Trader Management ────────────────────────────────────────


@router.get("/traders", response_model=List[TraderBrief])
async def list_traders(current_user: CAUser = Depends(get_current_user)):
    """List all traders managed by this CA."""
    traders = await get_rows(
        "traders",
        filters={"ca_id": current_user.id},
        order_by="created_at.desc",
    )
    return [TraderBrief(**t) for t in traders]


@router.post("/traders", response_model=TraderResponse, status_code=201)
async def create_trader(
    body: TraderCreate,
    current_user: CAUser = Depends(get_current_user),
):
    """Add a new trader."""
    settings = get_settings()

    # Generate munim email
    email_slug = body.business_name.lower().replace(" ", "-")[:20]
    munim_email = f"{email_slug}@{settings.cloudmailin_email_domain}"

    trader_data = {
        "ca_id": current_user.id,
        "business_name": body.business_name,
        "gstin": body.gstin,
        "phone": body.phone,
        "email": body.email,
        "state_code": body.state_code,
        "munim_email": munim_email,
        "onboarding_state": "ACTIVE",
    }

    created = await insert_row("traders", trader_data)
    return TraderResponse(**created)


# ── Dashboard Summary ────────────────────────────────────────


@router.get("/summary/{trader_id}", response_model=DashboardSummary)
async def get_summary(
    trader_id: str,
    current_user: CAUser = Depends(get_current_user),
):
    """Get the full dashboard summary for a trader."""
    await _verify_trader_access(trader_id, current_user.id)

    # ITC Summary
    invoices = await get_rows("invoices", filters={"trader_id": trader_id})

    itc = ITCSummary(
        total_invoices=len(invoices),
    )

    for inv in invoices:
        total_tax = sum([
            inv.get("cgst", 0) or 0,
            inv.get("sgst", 0) or 0,
            inv.get("igst", 0) or 0,
            inv.get("cess", 0) or 0,
        ])
        itc.total_itc += total_tax

        status = inv.get("itc_status", "PENDING")
        if status == "CONFIRMED":
            itc.confirmed += total_tax
        elif status == "AT_RISK":
            itc.at_risk += total_tax
        elif status == "FIXABLE_BLOCKED":
            itc.fixable_blocked += total_tax
        elif status == "INELIGIBLE":
            itc.ineligible += total_tax
        elif status == "FRAUD_FLAGGED":
            itc.fraud_flagged += total_tax
        else:
            itc.pending += total_tax

    # Action counts
    actions = await get_rows("action_items", filters={"trader_id": trader_id})
    unresolved = [a for a in actions if not a.get("is_resolved")]

    # Supplier counts
    suppliers = await get_rows("supplier_profiles", filters={"trader_id": trader_id})
    flagged = [s for s in suppliers if s.get("is_flagged")]

    # Upcoming deadlines
    today = date.today()
    deadlines_data = await get_rows(
        "compliance_deadlines",
        filters={"is_active": True},
        order_by="due_date",
        limit=5,
    )
    upcoming = []
    for d in deadlines_data:
        due = d.get("due_date")
        if isinstance(due, str):
            due = datetime.strptime(due, "%Y-%m-%d").date()
        if due and due >= today:
            days_remaining = (due - today).days
            upcoming.append(ComplianceDeadline(
                return_type=d["return_type"],
                period=d["period"],
                due_date=due,
                description=d.get("description"),
                days_remaining=days_remaining,
            ))

    # Recent invoices (last 30 days)
    thirty_days_ago = (datetime.now() - timedelta(days=30)).isoformat()
    recent = [
        inv for inv in invoices
        if inv.get("created_at") and str(inv["created_at"]) >= thirty_days_ago
    ]

    return DashboardSummary(
        itc_summary=itc,
        action_count=len(actions),
        unresolved_actions=len(unresolved),
        supplier_count=len(suppliers),
        flagged_suppliers=len(flagged),
        upcoming_deadlines=upcoming[:5],
        recent_invoices=len(recent),
    )


# ── Action Queue ─────────────────────────────────────────────


@router.get("/actions/{trader_id}", response_model=ActionListResponse)
async def get_actions(
    trader_id: str,
    resolved: Optional[bool] = Query(None),
    current_user: CAUser = Depends(get_current_user),
):
    """Get the prioritized action queue for a trader."""
    await _verify_trader_access(trader_id, current_user.id)

    filters = {"trader_id": trader_id}
    if resolved is not None:
        filters["is_resolved"] = resolved

    actions = await get_rows("action_items", filters=filters, order_by="created_at.desc")

    # Sort by severity (fraud → at_risk → fixable → low)
    action_items = [ActionItem(**a) for a in actions]
    action_items.sort(key=lambda x: SEVERITY_ORDER.get(x.severity, 99))

    unresolved = sum(1 for a in action_items if not a.is_resolved)

    return ActionListResponse(
        actions=action_items,
        total=len(action_items),
        unresolved=unresolved,
    )


@router.patch("/actions/{action_id}/resolve")
async def resolve_action(
    action_id: str,
    body: ActionResolve,
    current_user: CAUser = Depends(get_current_user),
):
    """Mark an action item as resolved."""
    action = await get_row_by_id("action_items", action_id)
    if not action:
        raise HTTPException(status_code=404, detail="Action not found")

    # Verify access
    await _verify_trader_access(action["trader_id"], current_user.id)

    updated = await update_row("action_items", action_id, {
        "is_resolved": True,
        "resolved_at": datetime.now().isoformat(),
        "resolved_by": current_user.id,
    })

    return {"status": "resolved", "action_id": action_id}


# ── Supplier Health ──────────────────────────────────────────


@router.get("/suppliers/{trader_id}", response_model=List[SupplierHealth])
async def get_suppliers(
    trader_id: str,
    flagged_only: bool = Query(False),
    current_user: CAUser = Depends(get_current_user),
):
    """Get supplier health data for a trader."""
    await _verify_trader_access(trader_id, current_user.id)

    filters = {"trader_id": trader_id}
    if flagged_only:
        filters["is_flagged"] = True

    suppliers = await get_rows(
        "supplier_profiles",
        filters=filters,
        order_by="compliance_score",
    )

    return [SupplierHealth(**s) for s in suppliers]


# ── Invoice Records ──────────────────────────────────────────


@router.get("/invoices/{trader_id}", response_model=InvoiceListResponse)
async def get_invoices(
    trader_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None),
    supplier_gstin: Optional[str] = Query(None),
    current_user: CAUser = Depends(get_current_user),
):
    """Get paginated invoice records for a trader."""
    await _verify_trader_access(trader_id, current_user.id)

    filters = {"trader_id": trader_id}
    if status:
        filters["itc_status"] = status
    if supplier_gstin:
        filters["supplier_gstin"] = supplier_gstin

    total = await count_rows("invoices", filters=filters)
    offset = (page - 1) * per_page

    invoices = await get_rows(
        "invoices",
        filters=filters,
        order_by="created_at.desc",
        limit=per_page,
        offset=offset,
    )

    return InvoiceListResponse(
        invoices=[InvoiceRecord(**inv) for inv in invoices],
        total=total,
        page=page,
        per_page=per_page,
    )


# ── ITC Timeline ────────────────────────────────────────────


@router.get("/itc-timeline/{trader_id}", response_model=List[ITCTimelinePoint])
async def get_itc_timeline(
    trader_id: str,
    months: int = Query(6, ge=1, le=12),
    current_user: CAUser = Depends(get_current_user),
):
    """Get ITC trend data for the last N months."""
    await _verify_trader_access(trader_id, current_user.id)

    invoices = await get_rows("invoices", filters={"trader_id": trader_id})

    # Group by period
    period_data = {}
    for inv in invoices:
        period = inv.get("period")
        if not period:
            continue

        if period not in period_data:
            period_data[period] = ITCTimelinePoint(period=period)

        point = period_data[period]
        total_tax = sum([
            inv.get("cgst", 0) or 0,
            inv.get("sgst", 0) or 0,
            inv.get("igst", 0) or 0,
            inv.get("cess", 0) or 0,
        ])

        status = inv.get("itc_status", "PENDING")
        if status == "CONFIRMED":
            point.confirmed += total_tax
        elif status in ("AT_RISK", "FIXABLE_BLOCKED", "PENDING"):
            point.at_risk += total_tax
        elif status == "INELIGIBLE":
            point.blocked += total_tax
        elif status == "FRAUD_FLAGGED":
            point.fraud_flagged += total_tax

        point.total += total_tax

    # Sort and limit to requested months
    timeline = sorted(period_data.values(), key=lambda x: x.period, reverse=True)[:months]
    timeline.reverse()

    return timeline
