"""
Supplier Health Monitoring Module.

Tracks each vendor's GSTR-1 filing consistency and flags chronically
non-compliant suppliers before they become a compliance problem.
"""

import logging
from typing import Dict, List, Optional

from app.models.action import ActionItem, ActionType, ActionSeverity

logger = logging.getLogger(__name__)

# Threshold below which a supplier is flagged
COMPLIANCE_THRESHOLD = 60.0  # percent


def calculate_compliance_score(
    months_filed: int,
    total_months_tracked: int,
) -> float:
    """
    Calculate a supplier's compliance score.

    Score = (months_filed / total_months_tracked) × 100.
    Returns 100 if no months are tracked yet.
    """
    if total_months_tracked <= 0:
        return 100.0
    return round((months_filed / total_months_tracked) * 100, 2)


def evaluate_supplier(
    supplier_profile: Dict,
    reconciliation_appeared_this_period: bool,
) -> Dict:
    """
    Evaluate a supplier's health after a reconciliation run.

    Updates the profile's tracking counters and compliance score.

    Args:
        supplier_profile: Current supplier profile dict from DB.
        reconciliation_appeared_this_period: Whether this supplier's invoices
            appeared in GSTR-2B for the current period.

    Returns:
        Updated supplier profile dict (to be written back to DB).
    """
    profile = dict(supplier_profile)

    # Increment tracking
    profile["total_months_tracked"] = profile.get("total_months_tracked", 0) + 1

    if reconciliation_appeared_this_period:
        profile["months_filed"] = profile.get("months_filed", 0) + 1

    # Recalculate compliance score
    score = calculate_compliance_score(
        profile["months_filed"],
        profile["total_months_tracked"],
    )
    profile["compliance_score"] = score

    # Flag if below threshold
    if score < COMPLIANCE_THRESHOLD and profile["total_months_tracked"] >= 3:
        profile["is_flagged"] = True
        profile["flag_reason"] = (
            f"Compliance score {score:.0f}% — filed {profile['months_filed']} "
            f"out of {profile['total_months_tracked']} tracked months"
        )
    else:
        profile["is_flagged"] = False
        profile["flag_reason"] = None

    return profile


def generate_supplier_action_items(
    trader_id: str,
    flagged_suppliers: List[Dict],
) -> List[ActionItem]:
    """
    Generate action items for flagged (non-compliant) suppliers.

    Args:
        trader_id: Trader UUID.
        flagged_suppliers: List of supplier profiles that are newly flagged.

    Returns:
        List of ActionItem objects to be persisted.
    """
    actions = []

    for supplier in flagged_suppliers:
        gstin = supplier.get("supplier_gstin", "N/A")
        name = supplier.get("supplier_name", "Unknown Supplier")
        score = supplier.get("compliance_score", 0)
        months_filed = supplier.get("months_filed", 0)
        total_months = supplier.get("total_months_tracked", 0)
        total_value = supplier.get("total_invoice_value", 0)

        actions.append(ActionItem(
            trader_id=trader_id,
            action_type=ActionType.SUPPLIER_NON_COMPLIANT,
            severity=ActionSeverity.HIGH if score < 40 else ActionSeverity.MEDIUM,
            title=f"Non-compliant supplier: {name}",
            description=(
                f"Supplier {name} (GSTIN: {gstin}) has a compliance score of {score:.0f}%. "
                f"Filed GSTR-1 only {months_filed} out of {total_months} tracked months. "
                f"Total invoice value from this supplier: ₹{total_value:,.2f}. "
                f"ITC from this supplier's invoices is at risk."
            ),
            affected_amount=total_value,
            recommended_fix=(
                f"Contact {name} and request they file their pending GSTR-1 returns. "
                f"Consider reducing or pausing transactions until compliance improves."
            ),
            vendor_gstin=gstin,
            vendor_name=name,
        ))

    return actions


def update_supplier_stats(
    profile: Dict,
    new_invoice_amount: float,
) -> Dict:
    """
    Update a supplier's running statistics when a new invoice is processed.

    Args:
        profile: Current supplier profile dict.
        new_invoice_amount: Amount of the new invoice.

    Returns:
        Updated profile dict.
    """
    profile = dict(profile)

    count = profile.get("total_invoice_count", 0) + 1
    total = profile.get("total_invoice_value", 0) + new_invoice_amount

    profile["total_invoice_count"] = count
    profile["total_invoice_value"] = round(total, 2)
    profile["average_invoice_value"] = round(total / count, 2) if count > 0 else 0

    return profile
