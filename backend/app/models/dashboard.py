"""
Pydantic models for dashboard summary data.
"""

from datetime import date
from typing import List, Optional

from pydantic import BaseModel, Field


class ITCSummary(BaseModel):
    """ITC breakdown for a trader."""
    total_itc: float = 0
    confirmed: float = 0
    at_risk: float = 0
    fixable_blocked: float = 0
    ineligible: float = 0
    fraud_flagged: float = 0
    pending: float = 0
    total_invoices: int = 0
    period: Optional[str] = None


class SupplierHealth(BaseModel):
    """Supplier health record for the dashboard."""
    supplier_gstin: str
    supplier_name: Optional[str] = None
    compliance_score: float = 100
    total_months_tracked: int = 0
    months_filed: int = 0
    total_invoice_count: int = 0
    total_invoice_value: float = 0
    average_invoice_value: float = 0
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    last_invoice_date: Optional[date] = None


class ITCTimelinePoint(BaseModel):
    """Single data point for the 6-month ITC trend chart."""
    period: str  # 'YYYY-MM'
    confirmed: float = 0
    at_risk: float = 0
    blocked: float = 0
    fraud_flagged: float = 0
    total: float = 0


class ComplianceDeadline(BaseModel):
    """Upcoming GST filing deadline."""
    return_type: str
    period: str
    due_date: date
    description: Optional[str] = None
    days_remaining: int = 0


class DashboardSummary(BaseModel):
    """Complete dashboard overview for a trader."""
    itc_summary: ITCSummary
    action_count: int = 0
    unresolved_actions: int = 0
    supplier_count: int = 0
    flagged_suppliers: int = 0
    upcoming_deadlines: List[ComplianceDeadline] = Field(default_factory=list)
    recent_invoices: int = 0
