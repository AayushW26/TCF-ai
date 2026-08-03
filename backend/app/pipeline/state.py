"""
Pipeline state definition for the LangGraph invoice processing graph.
"""

from typing import Any, Dict, List, Optional, TypedDict

from app.models.invoice import InvoiceExtraction, ITCResult, FraudResult
from app.services.deepvue_client import GSTINInfo
from app.domain.hsn import HSNValidationResult


class InvoicePipelineState(TypedDict, total=False):
    """
    State object passed through the LangGraph pipeline.

    Each node reads from and writes to this shared state.
    """

    # ── Input ────────────────────────────────────────────
    image_bytes: bytes
    mime_type: str
    trader_id: str
    source: str  # 'whatsapp', 'email', 'upload'

    # ── Node 1: Gemini Extraction ────────────────────────
    extraction: Optional[InvoiceExtraction]

    # ── Node 2: GSTIN Validation ─────────────────────────
    gstin_info: Optional[GSTINInfo]

    # ── Node 3: HSN Validation ───────────────────────────
    hsn_results: Optional[List[HSNValidationResult]]

    # ── Node 4: ITC Rules Engine ─────────────────────────
    itc_result: Optional[ITCResult]

    # ── Node 5: Fraud Scoring ────────────────────────────
    fraud_result: Optional[FraudResult]

    # ── Node 6: Save Results ─────────────────────────────
    invoice_id: Optional[str]
    action_items_created: int

    # ── Error Tracking ───────────────────────────────────
    errors: List[str]

    # ── Metadata ─────────────────────────────────────────
    trader_state_code: Optional[str]
    supplier_history: Optional[Dict[str, Any]]
