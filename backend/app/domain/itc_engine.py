"""
ITC (Input Tax Credit) Rules Engine — GST §16 + §17(5)

Pure deterministic rule-based implementation. Zero LLM involvement.
Classifies every invoice into one of five statuses:
  CONFIRMED / FIXABLE_BLOCKED / AT_RISK / INELIGIBLE / FRAUD_FLAGGED

Fully auditable logic — each decision comes with the exact section reference.
"""

import logging
import re
from datetime import datetime, date
from typing import List, Optional, Tuple

from app.models.invoice import (
    InvoiceExtraction,
    InvoiceRecord,
    ITCResult,
    ITCStatus,
    LineItem,
)

logger = logging.getLogger(__name__)


# ── §17(5) Blocked Credit Categories ────────────────────────
# Each category has: (name, blocked_section, HSN prefixes, keywords, exceptions)

BLOCKED_CATEGORIES = [
    {
        "name": "Motor Vehicles",
        "section": "§17(5)(a)",
        "hsn_prefixes": ["8702", "8703"],
        "keywords": ["car", "sedan", "suv", "motor vehicle", "automobile", "vehicle purchase"],
        "exception_keywords": ["further supply", "passenger transport", "driving school", "training"],
        "description": "Motor vehicles for passenger transport (≤13 seats) — ITC blocked unless used for further supply, passenger transport services, or training.",
    },
    {
        "name": "Food & Beverages",
        "section": "§17(5)(b)(i)",
        "hsn_prefixes": ["0901", "0902", "1901", "1902", "1905", "2101", "2102", "2103", "2104", "2105", "2106", "9963"],
        "keywords": ["food", "beverage", "restaurant", "meal", "snack", "canteen", "pantry", "tiffin"],
        "exception_keywords": ["further supply", "outward taxable supply of same category"],
        "description": "Food and beverages, outdoor catering — ITC blocked unless used to make an outward taxable supply of the same category.",
    },
    {
        "name": "Outdoor Catering",
        "section": "§17(5)(b)(i)",
        "hsn_prefixes": ["9963"],
        "keywords": ["outdoor catering", "catering service", "banquet", "event catering"],
        "exception_keywords": ["further supply", "outward taxable supply"],
        "description": "Outdoor catering services — ITC blocked unless used to provide outward taxable supply of same category.",
    },
    {
        "name": "Beauty Treatment",
        "section": "§17(5)(b)(i)",
        "hsn_prefixes": ["9602"],
        "keywords": ["beauty", "salon", "spa", "cosmetic", "beauty treatment", "parlour", "parlor"],
        "exception_keywords": ["further supply"],
        "description": "Beauty treatment services — ITC blocked unless used for further supply of same category.",
    },
    {
        "name": "Health & Fitness",
        "section": "§17(5)(b)(ii)",
        "hsn_prefixes": [],
        "keywords": ["gym", "fitness", "health club", "swimming pool", "yoga class", "gymnasium"],
        "exception_keywords": [],
        "description": "Health club, fitness centre, gym membership — ITC permanently blocked.",
    },
    {
        "name": "Club Membership",
        "section": "§17(5)(b)(ii)",
        "hsn_prefixes": [],
        "keywords": ["club membership", "club fee", "membership fee", "country club", "social club"],
        "exception_keywords": [],
        "description": "Club or recreational facility membership — ITC permanently blocked.",
    },
    {
        "name": "Rent-a-Cab",
        "section": "§17(5)(b)(iii)",
        "hsn_prefixes": ["9966"],
        "keywords": ["cab", "taxi", "rent-a-cab", "rental car", "chauffeur", "ola", "uber", "ride"],
        "exception_keywords": ["obligatory", "employee transport mandated", "further supply"],
        "description": "Rent-a-cab services — ITC blocked unless obligatory for employer or used for further supply.",
    },
    {
        "name": "Life / Health Insurance",
        "section": "§17(5)(b)(iii)",
        "hsn_prefixes": ["9971"],
        "keywords": ["insurance", "life insurance", "health insurance", "medical insurance", "group insurance"],
        "exception_keywords": ["obligatory", "mandated by law", "statutory", "further supply"],
        "description": "Life and health insurance — ITC blocked unless it is obligatory for employer to provide or used for further supply.",
    },
    {
        "name": "Travel Benefits (LTA)",
        "section": "§17(5)(b)(iv)",
        "hsn_prefixes": [],
        "keywords": ["travel benefit", "vacation", "lta", "leave travel", "holiday", "travel concession"],
        "exception_keywords": [],
        "description": "Employee travel / vacation benefits — ITC permanently blocked.",
    },
    {
        "name": "Works Contract (Immovable Property)",
        "section": "§17(5)(c)",
        "hsn_prefixes": ["9954"],
        "keywords": ["works contract", "construction", "civil work", "building construction", "renovation immovable"],
        "exception_keywords": ["further supply of works contract", "input service for works contract"],
        "description": "Works contract for construction of immovable property — ITC blocked unless used for further supply of works contract.",
    },
    {
        "name": "Self-Construction (Immovable Property)",
        "section": "§17(5)(d)",
        "hsn_prefixes": [],
        "keywords": ["self construction", "own account construction", "construction on own", "building own"],
        "exception_keywords": ["plant and machinery"],
        "description": "Construction of immovable property on own account — ITC blocked (except for plant and machinery).",
    },
    {
        "name": "Personal Consumption",
        "section": "§17(5)(g)",
        "hsn_prefixes": [],
        "keywords": ["personal", "gift", "self-use", "personal consumption", "personal use", "donation"],
        "exception_keywords": [],
        "description": "Goods or services used for personal consumption — ITC permanently blocked.",
    },
]

# State code mapping (first 2 digits of GSTIN → state)
STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab",
    "04": "Chandigarh", "05": "Uttarakhand", "06": "Haryana",
    "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh",
    "13": "Nagaland", "14": "Manipur", "15": "Mizoram",
    "16": "Tripura", "17": "Meghalaya", "18": "Assam",
    "19": "West Bengal", "20": "Jharkhand", "21": "Odisha",
    "22": "Chhattisgarh", "23": "Madhya Pradesh", "24": "Gujarat",
    "26": "Dadra & Nagar Haveli", "27": "Maharashtra",
    "29": "Karnataka", "30": "Goa", "31": "Lakshadweep",
    "32": "Kerala", "33": "Tamil Nadu", "34": "Puducherry",
    "35": "Andaman & Nicobar", "36": "Telangana", "37": "Andhra Pradesh",
    "38": "Ladakh",
}


def get_state_from_gstin(gstin: str) -> Optional[str]:
    """Extract state code (2-digit) from a GSTIN."""
    if gstin and len(gstin) >= 2:
        return gstin[:2]
    return None


def _check_blocked_categories(line_items: List[LineItem]) -> Optional[Tuple[str, str, str]]:
    """
    Check if any line item falls into a §17(5) blocked category.

    Returns (category_name, section, description) or None if not blocked.
    """
    for item in line_items:
        desc_lower = (item.description or "").lower()
        hsn = item.hsn_code or ""

        for cat in BLOCKED_CATEGORIES:
            matched = False

            # Check HSN prefix match
            for prefix in cat["hsn_prefixes"]:
                if hsn.startswith(prefix):
                    matched = True
                    break

            # Check keyword match
            if not matched:
                for keyword in cat["keywords"]:
                    if keyword.lower() in desc_lower:
                        matched = True
                        break

            # Check if an exception applies
            if matched:
                exception_applies = False
                for exc_keyword in cat["exception_keywords"]:
                    if exc_keyword.lower() in desc_lower:
                        exception_applies = True
                        break

                if not exception_applies:
                    return (cat["name"], cat["section"], cat["description"])

    return None


def _validate_gstin_format(gstin: str) -> bool:
    """Basic GSTIN format validation (15-char alphanumeric pattern)."""
    if not gstin:
        return False
    pattern = r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$"
    return bool(re.match(pattern, gstin.upper()))


def classify_invoice(
    extraction: "InvoiceExtraction",
    gstin_is_active: bool = True,
    gstin_days_since_registration: Optional[int] = None,
    is_in_gstr2b: bool = False,
    fraud_score: int = 0,
    payment_date: Optional[date] = None,
) -> ITCResult:
    """
    Run the full ITC eligibility analysis on an extracted invoice.

    This is the main entry point for the ITC Rules Engine.

    Args:
        extraction: Structured invoice data from Gemini.
        gstin_is_active: Whether the supplier's GSTIN is active.
        gstin_days_since_registration: Days since supplier GSTIN registration.
        is_in_gstr2b: Whether this invoice was found in GSTR-2B.
        fraud_score: Fraud score from the fraud engine (0-100).
        payment_date: Date when payment was made (for 180-day rule).

    Returns:
        ITCResult with status and reasoning.
    """
    total_tax = (
        (extraction.cgst or 0)
        + (extraction.sgst or 0)
        + (extraction.igst or 0)
        + (extraction.cess or 0)
    )

    # ── 1. Fraud check (highest priority) ────────────────
    if fraud_score >= 70:
        return ITCResult(
            status=ITCStatus.FRAUD_FLAGGED,
            blocked_reason=f"Fraud score {fraud_score}/100 exceeds threshold (≥70). Multiple fraud signals detected.",
            blocked_section="Fraud Detection Engine",
            affected_amount=total_tax,
            fix_suggestion="Investigate the supplier and invoice authenticity. Contact supplier directly.",
        )

    # ── 2. §17(5) Blocked credits ────────────────────────
    blocked = _check_blocked_categories(extraction.line_items)
    if blocked:
        cat_name, section, description = blocked
        return ITCResult(
            status=ITCStatus.INELIGIBLE,
            blocked_reason=f"Blocked under {section} — {cat_name}. {description}",
            blocked_section=section,
            affected_amount=total_tax,
            fix_suggestion=None,
        )

    # ── 3. §16(2)(a) — Valid tax document ────────────────
    if not extraction.invoice_number:
        return ITCResult(
            status=ITCStatus.FIXABLE_BLOCKED,
            blocked_reason="Missing invoice number — §16(2)(a) requires a valid tax invoice.",
            blocked_section="§16(2)(a)",
            affected_amount=total_tax,
            fix_suggestion="Request a proper tax invoice with invoice number from the supplier.",
        )

    if not extraction.supplier_gstin or not _validate_gstin_format(extraction.supplier_gstin):
        return ITCResult(
            status=ITCStatus.FIXABLE_BLOCKED,
            blocked_reason="Invalid or missing supplier GSTIN — §16(2)(a) requires supplier GSTIN on the invoice.",
            blocked_section="§16(2)(a)",
            affected_amount=total_tax,
            fix_suggestion="Request a corrected invoice with valid GSTIN from the supplier.",
        )

    # ── 4. GSTIN status check ────────────────────────────
    if not gstin_is_active:
        return ITCResult(
            status=ITCStatus.AT_RISK,
            blocked_reason="Supplier GSTIN is not active (cancelled/suspended). ITC may be denied.",
            blocked_section="§16(2)(c)",
            affected_amount=total_tax,
            fix_suggestion="Verify supplier GSTIN status. Avoid future transactions with this supplier.",
        )

    # ── 5. §16(2)(c) — GSTR-2B reflection ───────────────
    if not is_in_gstr2b:
        return ITCResult(
            status=ITCStatus.AT_RISK,
            blocked_reason="Invoice not found in GSTR-2B. Supplier may not have filed GSTR-1.",
            blocked_section="§16(2)(c)",
            affected_amount=total_tax,
            fix_suggestion="Contact supplier to ensure they file their GSTR-1 including this invoice.",
        )

    # ── 6. 180-day payment rule — §16(2) proviso ────────
    if extraction.invoice_date and payment_date is None:
        try:
            inv_date = datetime.strptime(extraction.invoice_date, "%Y-%m-%d").date()
            days_since_invoice = (date.today() - inv_date).days
            if days_since_invoice > 180:
                return ITCResult(
                    status=ITCStatus.AT_RISK,
                    blocked_reason=(
                        f"Invoice is {days_since_invoice} days old without confirmed payment. "
                        "§16(2) proviso requires payment within 180 days or ITC must be reversed with 18% interest."
                    ),
                    blocked_section="§16(2) Proviso",
                    affected_amount=total_tax,
                    fix_suggestion="Confirm payment to supplier. If unpaid beyond 180 days, reverse ITC in GSTR-3B.",
                )
        except ValueError:
            pass

    # ── 7. Low confidence extraction ─────────────────────
    if extraction.confidence_score < 0.6:
        return ITCResult(
            status=ITCStatus.FIXABLE_BLOCKED,
            blocked_reason=(
                f"Low extraction confidence ({extraction.confidence_score:.0%}). "
                "Some invoice details may be incorrect."
            ),
            blocked_section="Data Quality",
            affected_amount=total_tax,
            fix_suggestion="Re-upload a clearer image of the invoice for re-extraction.",
        )

    # ── 8. All checks passed ─────────────────────────────
    return ITCResult(
        status=ITCStatus.CONFIRMED,
        blocked_reason=None,
        blocked_section=None,
        affected_amount=total_tax,
        fix_suggestion=None,
    )
