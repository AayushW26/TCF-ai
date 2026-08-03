"""
Pydantic models for GSTR-2B records and reconciliation results.
"""

from datetime import date, datetime
from typing import Optional, List
from enum import Enum

from pydantic import BaseModel, Field

from app.models.invoice import ReconciliationMatchType


class GSTR2BRecord(BaseModel):
    """Single record from a GSTR-2B JSON upload."""
    id: Optional[str] = None
    trader_id: str
    period: str  # 'YYYY-MM'
    supplier_gstin: str
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    invoice_value: Optional[float] = None
    taxable_value: Optional[float] = None
    igst: float = 0
    cgst: float = 0
    sgst: float = 0
    cess: float = 0
    place_of_supply: Optional[str] = None
    reverse_charge: bool = False
    itc_available: bool = True


class GSTR2BUploadResponse(BaseModel):
    """Response after uploading a GSTR-2B file."""
    records_parsed: int
    records_stored: int
    period: str
    errors: List[str] = Field(default_factory=list)


class ReconciliationResult(BaseModel):
    """Result of a single reconciliation match attempt."""
    id: Optional[str] = None
    trader_id: str
    period: str
    invoice_id: Optional[str] = None
    gstr2b_id: Optional[str] = None
    match_type: ReconciliationMatchType
    match_confidence: Optional[float] = None
    amount_difference: Optional[float] = None
    date_difference: Optional[int] = None  # days
    details: dict = Field(default_factory=dict)


class ReconciliationSummary(BaseModel):
    """Summary of a reconciliation run."""
    total_invoices: int
    total_gstr2b_records: int
    exact_matches: int
    fuzzy_matches: int
    amount_date_matches: int
    unmatched_invoices: int
    unmatched_gstr2b: int
    action_items_created: int
