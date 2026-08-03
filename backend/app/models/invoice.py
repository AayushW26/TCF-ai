"""
Pydantic models for invoice data — extraction, storage, and API responses.
"""

from datetime import date, datetime
from typing import List, Optional
from enum import Enum

from pydantic import BaseModel, Field


class ITCStatus(str, Enum):
    CONFIRMED = "CONFIRMED"
    FIXABLE_BLOCKED = "FIXABLE_BLOCKED"
    AT_RISK = "AT_RISK"
    INELIGIBLE = "INELIGIBLE"
    FRAUD_FLAGGED = "FRAUD_FLAGGED"
    PENDING = "PENDING"


class ReconciliationMatchType(str, Enum):
    EXACT = "EXACT"
    FUZZY = "FUZZY"
    AMOUNT_DATE = "AMOUNT_DATE"
    UNMATCHED = "UNMATCHED"


class LineItem(BaseModel):
    """Single line item from an invoice."""
    description: Optional[str] = None
    hsn_code: Optional[str] = None
    quantity: Optional[float] = None
    rate: Optional[float] = None
    taxable_value: Optional[float] = None
    cgst_rate: Optional[float] = 0
    sgst_rate: Optional[float] = 0
    igst_rate: Optional[float] = 0
    cgst: Optional[float] = 0
    sgst: Optional[float] = 0
    igst: Optional[float] = 0
    cess: Optional[float] = 0


class InvoiceExtraction(BaseModel):
    """
    Structured output from Gemini Vision OCR.
    This is what the AI model returns after processing an invoice image.
    """
    supplier_name: Optional[str] = None
    supplier_gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[str] = None  # ISO date string
    place_of_supply: Optional[str] = None
    reverse_charge: bool = False
    line_items: List[LineItem] = Field(default_factory=list)
    total_taxable_value: Optional[float] = None
    cgst: Optional[float] = 0
    sgst: Optional[float] = 0
    igst: Optional[float] = 0
    cess: Optional[float] = 0
    total_amount: Optional[float] = None
    confidence_score: float = Field(default=0.0, ge=0.0, le=1.0)


class InvoiceRecord(BaseModel):
    """Full invoice record as stored in the database."""
    id: str
    trader_id: str
    supplier_name: Optional[str] = None
    supplier_gstin: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[date] = None
    total_taxable_value: Optional[float] = None
    cgst: float = 0
    sgst: float = 0
    igst: float = 0
    cess: float = 0
    total_amount: Optional[float] = None
    place_of_supply: Optional[str] = None
    reverse_charge: bool = False
    itc_status: ITCStatus = ITCStatus.PENDING
    itc_blocked_reason: Optional[str] = None
    itc_blocked_section: Optional[str] = None
    fraud_score: int = 0
    fraud_signals: list = Field(default_factory=list)
    extraction_confidence: float = 0.0
    source: str = "whatsapp"
    period: Optional[str] = None
    reconciliation_status: ReconciliationMatchType = ReconciliationMatchType.UNMATCHED
    created_at: Optional[datetime] = None


class InvoiceListResponse(BaseModel):
    """Paginated list of invoices."""
    invoices: List[InvoiceRecord]
    total: int
    page: int = 1
    per_page: int = 20


class ITCResult(BaseModel):
    """Result of ITC eligibility check from the rules engine."""
    status: ITCStatus
    blocked_reason: Optional[str] = None
    blocked_section: Optional[str] = None
    affected_amount: float = 0
    fix_suggestion: Optional[str] = None


class FraudResult(BaseModel):
    """Result of the 6-signal fraud scoring engine."""
    total_score: int = 0
    signals: List[dict] = Field(default_factory=list)
    is_flagged: bool = False
    is_soft_flag: bool = False
