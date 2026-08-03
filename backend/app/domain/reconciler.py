"""
GSTR-2B Three-Pass Fuzzy Reconciliation Engine

Matches invoice records against GSTR-2B entries using:
  Pass 1 (Exact):       GSTIN + invoice_number + date — all exact match
  Pass 2 (Fuzzy):       Levenshtein ≤3 on invoice_number, ±2% amount, ±15 days
  Pass 3 (Amount+Date): Fallback — GSTIN + amount ±2% + date ±15 days

Unmatched entries generate ActionItem records.
No LLM involvement — purely deterministic.
"""

import logging
from datetime import date, timedelta
from typing import Dict, List, Optional, Tuple

from rapidfuzz import fuzz
from Levenshtein import distance as levenshtein_distance

from app.models.invoice import InvoiceRecord, ReconciliationMatchType
from app.models.gstr2b import GSTR2BRecord, ReconciliationResult, ReconciliationSummary
from app.models.action import ActionItem, ActionType, ActionSeverity

logger = logging.getLogger(__name__)

# Tolerances
AMOUNT_TOLERANCE_PERCENT = 0.02  # ±2%
DATE_TOLERANCE_DAYS = 15
LEVENSHTEIN_MAX_DISTANCE = 3


def _normalise_invoice_number(inv_num: Optional[str]) -> str:
    """
    Normalise an invoice number for comparison.
    Removes common separators and converts to uppercase.
    """
    if not inv_num:
        return ""
    return inv_num.upper().replace("-", "").replace("/", "").replace(" ", "").replace(".", "")


def _amounts_match(a: Optional[float], b: Optional[float], tolerance: float = AMOUNT_TOLERANCE_PERCENT) -> bool:
    """Check if two amounts are within tolerance."""
    if a is None or b is None:
        return False
    if a == 0 and b == 0:
        return True
    if a == 0 or b == 0:
        return False
    return abs(a - b) / max(abs(a), abs(b)) <= tolerance


def _dates_match(d1: Optional[date], d2: Optional[date], tolerance_days: int = DATE_TOLERANCE_DAYS) -> bool:
    """Check if two dates are within tolerance."""
    if d1 is None or d2 is None:
        return False
    return abs((d1 - d2).days) <= tolerance_days


def _dates_exact(d1: Optional[date], d2: Optional[date]) -> bool:
    """Check if two dates are exactly the same."""
    if d1 is None or d2 is None:
        return False
    return d1 == d2


def _parse_date(date_val) -> Optional[date]:
    """Safely parse a date value."""
    if isinstance(date_val, date):
        return date_val
    if isinstance(date_val, str):
        try:
            from datetime import datetime
            return datetime.strptime(date_val, "%Y-%m-%d").date()
        except ValueError:
            return None
    return None


def reconcile(
    invoices: List[Dict],
    gstr2b_records: List[Dict],
    trader_id: str,
    period: str,
) -> Tuple[List[ReconciliationResult], ReconciliationSummary, List[ActionItem]]:
    """
    Run the 3-pass reconciliation between invoice records and GSTR-2B entries.

    Args:
        invoices: List of invoice dicts from the database.
        gstr2b_records: List of GSTR-2B record dicts from the database.
        trader_id: Trader UUID.
        period: Tax period (YYYY-MM).

    Returns:
        Tuple of (results, summary, action_items).
    """
    results: List[ReconciliationResult] = []
    action_items: List[ActionItem] = []

    # Track which records have been matched
    matched_invoice_ids = set()
    matched_gstr2b_ids = set()

    # Pre-process: group by supplier GSTIN for efficiency
    inv_by_gstin: Dict[str, List[Dict]] = {}
    for inv in invoices:
        gstin = inv.get("supplier_gstin", "")
        if gstin:
            inv_by_gstin.setdefault(gstin, []).append(inv)

    g2b_by_gstin: Dict[str, List[Dict]] = {}
    for g2b in gstr2b_records:
        gstin = g2b.get("supplier_gstin", "")
        if gstin:
            g2b_by_gstin.setdefault(gstin, []).append(g2b)

    # ── Pass 1: Exact Match ──────────────────────────────
    logger.info("Reconciliation Pass 1 (Exact) — %d invoices vs %d GSTR-2B records", len(invoices), len(gstr2b_records))

    for gstin, inv_list in inv_by_gstin.items():
        g2b_list = g2b_by_gstin.get(gstin, [])
        for inv in inv_list:
            if inv["id"] in matched_invoice_ids:
                continue
            inv_num_norm = _normalise_invoice_number(inv.get("invoice_number"))
            inv_date = _parse_date(inv.get("invoice_date"))

            for g2b in g2b_list:
                if g2b["id"] in matched_gstr2b_ids:
                    continue
                g2b_num_norm = _normalise_invoice_number(g2b.get("invoice_number"))
                g2b_date = _parse_date(g2b.get("invoice_date"))

                if inv_num_norm and g2b_num_norm and inv_num_norm == g2b_num_norm and _dates_exact(inv_date, g2b_date):
                    # Exact match!
                    amount_diff = (inv.get("total_amount") or 0) - (g2b.get("invoice_value") or 0)

                    results.append(ReconciliationResult(
                        trader_id=trader_id,
                        period=period,
                        invoice_id=inv["id"],
                        gstr2b_id=g2b["id"],
                        match_type=ReconciliationMatchType.EXACT,
                        match_confidence=100.0,
                        amount_difference=round(amount_diff, 2),
                        date_difference=0,
                        details={"pass": 1, "method": "exact"},
                    ))
                    matched_invoice_ids.add(inv["id"])
                    matched_gstr2b_ids.add(g2b["id"])
                    break

    # ── Pass 2: Fuzzy Match ──────────────────────────────
    logger.info("Reconciliation Pass 2 (Fuzzy) — %d unmatched invoices", len(invoices) - len(matched_invoice_ids))

    for gstin, inv_list in inv_by_gstin.items():
        g2b_list = g2b_by_gstin.get(gstin, [])
        for inv in inv_list:
            if inv["id"] in matched_invoice_ids:
                continue
            inv_num_norm = _normalise_invoice_number(inv.get("invoice_number"))
            inv_date = _parse_date(inv.get("invoice_date"))
            inv_amount = inv.get("total_amount")

            best_match = None
            best_confidence = 0

            for g2b in g2b_list:
                if g2b["id"] in matched_gstr2b_ids:
                    continue
                g2b_num_norm = _normalise_invoice_number(g2b.get("invoice_number"))
                g2b_date = _parse_date(g2b.get("invoice_date"))
                g2b_amount = g2b.get("invoice_value")

                # Levenshtein on invoice number
                if inv_num_norm and g2b_num_norm:
                    lev_dist = levenshtein_distance(inv_num_norm, g2b_num_norm)
                else:
                    lev_dist = 999

                # Check fuzzy criteria
                num_match = lev_dist <= LEVENSHTEIN_MAX_DISTANCE
                amt_match = _amounts_match(inv_amount, g2b_amount)
                date_match = _dates_match(inv_date, g2b_date)

                if num_match and amt_match and date_match:
                    # Calculate confidence based on how close the match is
                    num_score = max(0, (LEVENSHTEIN_MAX_DISTANCE - lev_dist) / LEVENSHTEIN_MAX_DISTANCE * 40)
                    amt_score = 30 if amt_match else 0
                    date_score = 30 if date_match else 0
                    confidence = num_score + amt_score + date_score

                    if confidence > best_confidence:
                        best_confidence = confidence
                        date_diff = abs((inv_date - g2b_date).days) if inv_date and g2b_date else None
                        amount_diff = (inv_amount or 0) - (g2b_amount or 0)
                        best_match = (g2b, confidence, amount_diff, date_diff)

            if best_match:
                g2b, confidence, amount_diff, date_diff = best_match
                results.append(ReconciliationResult(
                    trader_id=trader_id,
                    period=period,
                    invoice_id=inv["id"],
                    gstr2b_id=g2b["id"],
                    match_type=ReconciliationMatchType.FUZZY,
                    match_confidence=round(confidence, 2),
                    amount_difference=round(amount_diff, 2),
                    date_difference=date_diff,
                    details={"pass": 2, "method": "fuzzy", "levenshtein_distance": lev_dist},
                ))
                matched_invoice_ids.add(inv["id"])
                matched_gstr2b_ids.add(g2b["id"])

    # ── Pass 3: Amount + Date Fallback ───────────────────
    logger.info("Reconciliation Pass 3 (Amount+Date) — %d unmatched invoices", len(invoices) - len(matched_invoice_ids))

    for gstin, inv_list in inv_by_gstin.items():
        g2b_list = g2b_by_gstin.get(gstin, [])
        for inv in inv_list:
            if inv["id"] in matched_invoice_ids:
                continue
            inv_date = _parse_date(inv.get("invoice_date"))
            inv_amount = inv.get("total_amount")

            for g2b in g2b_list:
                if g2b["id"] in matched_gstr2b_ids:
                    continue
                g2b_date = _parse_date(g2b.get("invoice_date"))
                g2b_amount = g2b.get("invoice_value")

                if _amounts_match(inv_amount, g2b_amount) and _dates_match(inv_date, g2b_date):
                    date_diff = abs((inv_date - g2b_date).days) if inv_date and g2b_date else None
                    amount_diff = (inv_amount or 0) - (g2b_amount or 0)

                    results.append(ReconciliationResult(
                        trader_id=trader_id,
                        period=period,
                        invoice_id=inv["id"],
                        gstr2b_id=g2b["id"],
                        match_type=ReconciliationMatchType.AMOUNT_DATE,
                        match_confidence=60.0,
                        amount_difference=round(amount_diff, 2),
                        date_difference=date_diff,
                        details={"pass": 3, "method": "amount_date"},
                    ))
                    matched_invoice_ids.add(inv["id"])
                    matched_gstr2b_ids.add(g2b["id"])
                    break

    # ── Generate Action Items for Unmatched ──────────────
    for inv in invoices:
        if inv["id"] not in matched_invoice_ids:
            total_tax = sum([
                inv.get("cgst", 0) or 0,
                inv.get("sgst", 0) or 0,
                inv.get("igst", 0) or 0,
                inv.get("cess", 0) or 0,
            ])

            action_items.append(ActionItem(
                trader_id=trader_id,
                invoice_id=inv["id"],
                action_type=ActionType.RECONCILIATION_MISMATCH,
                severity=ActionSeverity.HIGH if total_tax > 10000 else ActionSeverity.MEDIUM,
                title=f"Invoice not found in GSTR-2B",
                description=(
                    f"Invoice {inv.get('invoice_number', 'N/A')} from {inv.get('supplier_name', 'Unknown')} "
                    f"(GSTIN: {inv.get('supplier_gstin', 'N/A')}) for ₹{inv.get('total_amount', 0):,.2f} "
                    f"was not found in GSTR-2B for period {period}. ITC of ₹{total_tax:,.2f} is at risk."
                ),
                affected_amount=total_tax,
                recommended_fix="Contact supplier to ensure they include this invoice in their GSTR-1 filing.",
                vendor_gstin=inv.get("supplier_gstin"),
                vendor_name=inv.get("supplier_name"),
            ))

    # Unmatched GSTR-2B records (supplier filed but we don't have the invoice)
    for g2b in gstr2b_records:
        if g2b["id"] not in matched_gstr2b_ids:
            results.append(ReconciliationResult(
                trader_id=trader_id,
                period=period,
                invoice_id=None,
                gstr2b_id=g2b["id"],
                match_type=ReconciliationMatchType.UNMATCHED,
                match_confidence=0,
                details={"pass": 0, "method": "unmatched_gstr2b"},
            ))

    # ── Build Summary ────────────────────────────────────
    summary = ReconciliationSummary(
        total_invoices=len(invoices),
        total_gstr2b_records=len(gstr2b_records),
        exact_matches=sum(1 for r in results if r.match_type == ReconciliationMatchType.EXACT),
        fuzzy_matches=sum(1 for r in results if r.match_type == ReconciliationMatchType.FUZZY),
        amount_date_matches=sum(1 for r in results if r.match_type == ReconciliationMatchType.AMOUNT_DATE),
        unmatched_invoices=len(invoices) - len(matched_invoice_ids),
        unmatched_gstr2b=len(gstr2b_records) - len(matched_gstr2b_ids),
        action_items_created=len(action_items),
    )

    logger.info(
        "Reconciliation complete for %s period %s: %d exact, %d fuzzy, %d amount+date, %d unmatched invoices",
        trader_id, period,
        summary.exact_matches, summary.fuzzy_matches,
        summary.amount_date_matches, summary.unmatched_invoices,
    )

    return results, summary, action_items
