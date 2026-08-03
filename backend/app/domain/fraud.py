"""
6-Signal Fraud Scoring Engine (0–100)

Each signal contributes a weighted score. Deterministic — no LLM.

Signals:
  1. GSTIN Age             (15 pts)
  2. Benford's Law         (20 pts)
  3. Sequential Invoices   (20 pts)
  4. Business Type Mismatch(15 pts)
  5. Geographic Mismatch   (15 pts)
  6. Velocity Anomaly      (15 pts)

Score ≥ 70 → FRAUD_FLAGGED
Score 40–69 → soft flag for CA review
Score < 40 → clean
"""

import logging
import math
import re
from collections import Counter
from typing import Dict, List, Optional

from scipy import stats as scipy_stats

from app.models.invoice import InvoiceExtraction, FraudResult
from app.services.deepvue_client import GSTINInfo

logger = logging.getLogger(__name__)


# ── Signal Weights ───────────────────────────────────────────

WEIGHTS = {
    "gstin_age": 15,
    "benfords_law": 20,
    "sequential_invoices": 20,
    "business_type_mismatch": 15,
    "geographic_mismatch": 15,
    "velocity_anomaly": 15,
}

# Benford's law expected distribution for leading digits 1-9
BENFORD_EXPECTED = {
    1: 0.301, 2: 0.176, 3: 0.125, 4: 0.097, 5: 0.079,
    6: 0.067, 7: 0.058, 8: 0.051, 9: 0.046,
}

# Business type → expected HSN categories mapping
# If supplier's registered business type doesn't match the goods/services
# in the invoice, it's suspicious.
BUSINESS_HSN_MAP = {
    "manufacturer": ["01-24", "25-40", "41-63", "64-71", "72-83", "84-97"],
    "trader": ["01-97"],  # Traders can sell anything
    "service provider": ["99"],  # SAC codes start with 99
    "composition": ["01-97"],
}


def _signal_gstin_age(
    gstin_info: Optional[GSTINInfo],
) -> tuple[int, dict]:
    """
    Signal 1: New GSTIN (<180 days) issuing invoices is suspicious.
    """
    if not gstin_info or gstin_info.days_since_registration is None:
        return 0, {"signal": "gstin_age", "score": 0, "reason": "GSTIN info unavailable"}

    days = gstin_info.days_since_registration

    if days < 180:
        return WEIGHTS["gstin_age"], {
            "signal": "gstin_age",
            "score": WEIGHTS["gstin_age"],
            "reason": f"GSTIN registered only {days} days ago (<180 days threshold)",
            "days_since_registration": days,
        }
    elif days < 365:
        score = WEIGHTS["gstin_age"] // 2
        return score, {
            "signal": "gstin_age",
            "score": score,
            "reason": f"GSTIN registered {days} days ago (relatively new, <365 days)",
            "days_since_registration": days,
        }

    return 0, {"signal": "gstin_age", "score": 0, "reason": "GSTIN age is acceptable", "days_since_registration": days}


def _signal_benfords_law(
    historical_amounts: List[float],
) -> tuple[int, dict]:
    """
    Signal 2: Benford's Law — check if leading-digit distribution is natural.
    Uses chi-squared test. Requires at least 10 data points.
    """
    if len(historical_amounts) < 10:
        return 0, {
            "signal": "benfords_law",
            "score": 0,
            "reason": f"Insufficient data ({len(historical_amounts)} invoices, need ≥10)",
        }

    # Extract leading digits
    leading_digits = []
    for amount in historical_amounts:
        if amount > 0:
            leading_digit = int(str(abs(amount)).lstrip("0").replace(".", "")[0])
            if 1 <= leading_digit <= 9:
                leading_digits.append(leading_digit)

    if len(leading_digits) < 10:
        return 0, {"signal": "benfords_law", "score": 0, "reason": "Insufficient valid leading digits"}

    n = len(leading_digits)
    digit_counts = Counter(leading_digits)

    # Chi-squared test against Benford's distribution
    observed = [digit_counts.get(d, 0) for d in range(1, 10)]
    expected = [BENFORD_EXPECTED[d] * n for d in range(1, 10)]

    chi2, p_value = scipy_stats.chisquare(observed, f_exp=expected)

    if p_value < 0.05:
        return WEIGHTS["benfords_law"], {
            "signal": "benfords_law",
            "score": WEIGHTS["benfords_law"],
            "reason": f"Leading-digit distribution violates Benford's Law (χ²={chi2:.2f}, p={p_value:.4f})",
            "chi_squared": round(chi2, 2),
            "p_value": round(p_value, 4),
        }

    return 0, {
        "signal": "benfords_law",
        "score": 0,
        "reason": "Leading-digit distribution follows Benford's Law",
        "p_value": round(p_value, 4),
    }


def _extract_invoice_serial(invoice_number: str) -> Optional[int]:
    """Extract numeric serial from an invoice number string."""
    if not invoice_number:
        return None
    # Find trailing digits: "INV-001" → 1, "GST/2026/0042" → 42
    match = re.search(r"(\d+)\s*$", invoice_number)
    if match:
        return int(match.group(1))
    return None


def _signal_sequential_invoices(
    current_invoice_number: Optional[str],
    historical_invoice_numbers: List[str],
) -> tuple[int, dict]:
    """
    Signal 3: Sequential invoice numbers from same supplier = classic fake invoice pattern.
    Checks if the current invoice serial is consecutive with recent ones.
    """
    if not current_invoice_number or len(historical_invoice_numbers) < 2:
        return 0, {
            "signal": "sequential_invoices",
            "score": 0,
            "reason": "Insufficient invoice history for sequential check",
        }

    current_serial = _extract_invoice_serial(current_invoice_number)
    if current_serial is None:
        return 0, {"signal": "sequential_invoices", "score": 0, "reason": "Cannot extract serial number"}

    historical_serials = sorted(
        [s for s in [_extract_invoice_serial(n) for n in historical_invoice_numbers] if s is not None]
    )

    if len(historical_serials) < 2:
        return 0, {"signal": "sequential_invoices", "score": 0, "reason": "Insufficient numeric serials"}

    # Check if the recent serials are perfectly consecutive
    all_serials = sorted(historical_serials + [current_serial])
    consecutive_count = 0

    for i in range(1, len(all_serials)):
        if all_serials[i] == all_serials[i - 1] + 1:
            consecutive_count += 1

    # If ≥3 consecutive invoice numbers → suspicious
    if consecutive_count >= 3:
        return WEIGHTS["sequential_invoices"], {
            "signal": "sequential_invoices",
            "score": WEIGHTS["sequential_invoices"],
            "reason": f"{consecutive_count + 1} consecutive invoice serial numbers detected — possible fake invoicing",
            "consecutive_count": consecutive_count + 1,
            "serials": all_serials[-5:],
        }
    elif consecutive_count >= 2:
        score = WEIGHTS["sequential_invoices"] // 2
        return score, {
            "signal": "sequential_invoices",
            "score": score,
            "reason": f"{consecutive_count + 1} sequential serials detected — mild concern",
            "consecutive_count": consecutive_count + 1,
        }

    return 0, {"signal": "sequential_invoices", "score": 0, "reason": "No sequential pattern detected"}


def _signal_business_type_mismatch(
    gstin_info: Optional[GSTINInfo],
    extraction: InvoiceExtraction,
) -> tuple[int, dict]:
    """
    Signal 4: Supplier's registered business type contradicts invoice line items.
    E.g., a "service provider" GSTIN selling physical goods.
    """
    if not gstin_info or not gstin_info.business_type:
        return 0, {
            "signal": "business_type_mismatch",
            "score": 0,
            "reason": "Supplier business type unavailable",
        }

    biz_type = gstin_info.business_type.lower()
    has_goods = False
    has_services = False

    for item in extraction.line_items:
        hsn = item.hsn_code or ""
        if hsn.startswith("99"):
            has_services = True
        elif hsn and len(hsn) >= 2:
            has_goods = True

    # Service provider selling goods (non-99 HSN codes)
    if "service" in biz_type and has_goods and not has_services:
        return WEIGHTS["business_type_mismatch"], {
            "signal": "business_type_mismatch",
            "score": WEIGHTS["business_type_mismatch"],
            "reason": f"Supplier registered as '{gstin_info.business_type}' but invoice contains goods (non-SAC HSN codes)",
            "business_type": gstin_info.business_type,
        }

    return 0, {
        "signal": "business_type_mismatch",
        "score": 0,
        "reason": "Business type is consistent with invoice items",
    }


def _signal_geographic_mismatch(
    supplier_gstin: Optional[str],
    buyer_state_code: Optional[str],
    extraction: InvoiceExtraction,
) -> tuple[int, dict]:
    """
    Signal 5: Supplier state ≠ buyer state but no IGST charged.
    In GST, inter-state supply must have IGST, not CGST/SGST.
    """
    if not supplier_gstin or not buyer_state_code:
        return 0, {
            "signal": "geographic_mismatch",
            "score": 0,
            "reason": "Insufficient state information for geographic check",
        }

    supplier_state = supplier_gstin[:2] if len(supplier_gstin) >= 2 else None
    if not supplier_state:
        return 0, {"signal": "geographic_mismatch", "score": 0, "reason": "Cannot determine supplier state"}

    states_match = supplier_state == buyer_state_code

    igst = extraction.igst or 0
    cgst = extraction.cgst or 0
    sgst = extraction.sgst or 0

    # Inter-state supply without IGST
    if not states_match and igst == 0 and (cgst > 0 or sgst > 0):
        return WEIGHTS["geographic_mismatch"], {
            "signal": "geographic_mismatch",
            "score": WEIGHTS["geographic_mismatch"],
            "reason": (
                f"Inter-state supply (supplier: {supplier_state}, buyer: {buyer_state_code}) "
                "but CGST/SGST charged instead of IGST"
            ),
            "supplier_state": supplier_state,
            "buyer_state": buyer_state_code,
        }

    # Intra-state supply with IGST (also wrong, but less common fraud)
    if states_match and igst > 0 and cgst == 0 and sgst == 0:
        score = WEIGHTS["geographic_mismatch"] // 2
        return score, {
            "signal": "geographic_mismatch",
            "score": score,
            "reason": (
                f"Intra-state supply (both in state {supplier_state}) "
                "but IGST charged instead of CGST/SGST"
            ),
            "supplier_state": supplier_state,
            "buyer_state": buyer_state_code,
        }

    return 0, {"signal": "geographic_mismatch", "score": 0, "reason": "Tax type is consistent with geography"}


def _signal_velocity_anomaly(
    current_amount: Optional[float],
    historical_average: Optional[float],
) -> tuple[int, dict]:
    """
    Signal 6: Invoice amount >5× the supplier's historical average.
    """
    if current_amount is None or historical_average is None or historical_average <= 0:
        return 0, {
            "signal": "velocity_anomaly",
            "score": 0,
            "reason": "Insufficient historical data for velocity check",
        }

    ratio = current_amount / historical_average

    if ratio > 5:
        return WEIGHTS["velocity_anomaly"], {
            "signal": "velocity_anomaly",
            "score": WEIGHTS["velocity_anomaly"],
            "reason": (
                f"Invoice amount ₹{current_amount:,.2f} is {ratio:.1f}× the supplier's "
                f"historical average (₹{historical_average:,.2f})"
            ),
            "ratio": round(ratio, 1),
            "current_amount": current_amount,
            "historical_average": round(historical_average, 2),
        }
    elif ratio > 3:
        score = WEIGHTS["velocity_anomaly"] // 2
        return score, {
            "signal": "velocity_anomaly",
            "score": score,
            "reason": (
                f"Invoice amount ₹{current_amount:,.2f} is {ratio:.1f}× the supplier's "
                f"historical average (₹{historical_average:,.2f}) — elevated"
            ),
            "ratio": round(ratio, 1),
        }

    return 0, {
        "signal": "velocity_anomaly",
        "score": 0,
        "reason": "Invoice amount is within normal range",
        "ratio": round(ratio, 1),
    }


def score_fraud(
    extraction: InvoiceExtraction,
    gstin_info: Optional[GSTINInfo] = None,
    buyer_state_code: Optional[str] = None,
    historical_amounts: Optional[List[float]] = None,
    historical_invoice_numbers: Optional[List[str]] = None,
    supplier_average_amount: Optional[float] = None,
) -> FraudResult:
    """
    Run the full 6-signal fraud scoring engine on an invoice.

    Args:
        extraction: Structured invoice data.
        gstin_info: Supplier GSTIN details from DeepVue.
        buyer_state_code: Buyer's state code (2 digits).
        historical_amounts: List of past invoice amounts from this supplier.
        historical_invoice_numbers: List of past invoice numbers from this supplier.
        supplier_average_amount: Pre-computed supplier average invoice amount.

    Returns:
        FraudResult with total score and individual signal details.
    """
    signals = []
    total_score = 0

    # Signal 1: GSTIN Age
    score, detail = _signal_gstin_age(gstin_info)
    total_score += score
    signals.append(detail)

    # Signal 2: Benford's Law
    score, detail = _signal_benfords_law(historical_amounts or [])
    total_score += score
    signals.append(detail)

    # Signal 3: Sequential Invoices
    score, detail = _signal_sequential_invoices(
        extraction.invoice_number,
        historical_invoice_numbers or [],
    )
    total_score += score
    signals.append(detail)

    # Signal 4: Business Type Mismatch
    score, detail = _signal_business_type_mismatch(gstin_info, extraction)
    total_score += score
    signals.append(detail)

    # Signal 5: Geographic Mismatch
    score, detail = _signal_geographic_mismatch(
        extraction.supplier_gstin,
        buyer_state_code,
        extraction,
    )
    total_score += score
    signals.append(detail)

    # Signal 6: Velocity Anomaly
    avg = supplier_average_amount
    if avg is None and historical_amounts:
        avg = sum(historical_amounts) / len(historical_amounts) if historical_amounts else None

    score, detail = _signal_velocity_anomaly(extraction.total_amount, avg)
    total_score += score
    signals.append(detail)

    # Determine flag status
    is_flagged = total_score >= 70
    is_soft_flag = 40 <= total_score < 70

    result = FraudResult(
        total_score=total_score,
        signals=signals,
        is_flagged=is_flagged,
        is_soft_flag=is_soft_flag,
    )

    logger.info(
        "Fraud score for invoice %s: %d/100 (flagged=%s, soft_flag=%s)",
        extraction.invoice_number,
        total_score,
        is_flagged,
        is_soft_flag,
    )

    return result
