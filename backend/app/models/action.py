"""
Pydantic models for action items (prioritized action queue).
"""

from datetime import datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field


class ActionType(str, Enum):
    FRAUD_FLAG = "FRAUD_FLAG"
    ITC_AT_RISK = "ITC_AT_RISK"
    FIXABLE_BLOCK = "FIXABLE_BLOCK"
    SUPPLIER_NON_COMPLIANT = "SUPPLIER_NON_COMPLIANT"
    RECONCILIATION_MISMATCH = "RECONCILIATION_MISMATCH"
    MISSING_DOCUMENT = "MISSING_DOCUMENT"


class ActionSeverity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


# Severity ranking for sorting (lower = more urgent)
SEVERITY_ORDER = {
    ActionSeverity.CRITICAL: 0,
    ActionSeverity.HIGH: 1,
    ActionSeverity.MEDIUM: 2,
    ActionSeverity.LOW: 3,
}


class ActionItem(BaseModel):
    """An item in the prioritized action queue."""
    id: Optional[str] = None
    trader_id: str
    invoice_id: Optional[str] = None
    action_type: ActionType
    severity: ActionSeverity
    title: str
    description: str
    affected_amount: float = 0
    recommended_fix: Optional[str] = None
    vendor_gstin: Optional[str] = None
    vendor_name: Optional[str] = None
    vendor_phone: Optional[str] = None
    vendor_email: Optional[str] = None
    is_resolved: bool = False
    resolved_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class ActionResolve(BaseModel):
    """Request body for resolving an action item."""
    resolution_note: Optional[str] = None


class ActionListResponse(BaseModel):
    """List of action items with counts."""
    actions: List[ActionItem]
    total: int
    unresolved: int
