"""
LangGraph StateGraph wiring for the invoice processing pipeline.

Graph:
  extract → validate_gstin → validate_hsn → score_fraud → itc_rules → save

Error handling: if any node fails, the pipeline continues to the next
node with error details attached to state. The save node always runs
to persist whatever partial results are available.
"""

import logging
from typing import Any, Dict

from langgraph.graph import StateGraph, END

from app.pipeline.state import InvoicePipelineState
from app.pipeline.nodes import (
    extract_invoice_node,
    validate_gstin_node,
    validate_hsn_node,
    apply_itc_rules_node,
    score_fraud_node,
    save_results_node,
)

logger = logging.getLogger(__name__)


def build_invoice_pipeline() -> StateGraph:
    """
    Build and compile the LangGraph invoice processing pipeline.

    Returns:
        Compiled StateGraph ready for invocation.
    """
    graph = StateGraph(InvoicePipelineState)

    # Add nodes
    graph.add_node("extract", extract_invoice_node)
    graph.add_node("validate_gstin", validate_gstin_node)
    graph.add_node("validate_hsn", validate_hsn_node)
    graph.add_node("score_fraud", score_fraud_node)
    graph.add_node("itc_rules", apply_itc_rules_node)
    graph.add_node("save", save_results_node)

    # Define edges (linear pipeline with error resilience)
    graph.set_entry_point("extract")
    graph.add_edge("extract", "validate_gstin")
    graph.add_edge("validate_gstin", "validate_hsn")
    graph.add_edge("validate_hsn", "score_fraud")
    graph.add_edge("score_fraud", "itc_rules")
    graph.add_edge("itc_rules", "save")
    graph.add_edge("save", END)

    return graph.compile()


# Module-level compiled pipeline (singleton)
_pipeline = None


def get_pipeline():
    """Get or create the compiled pipeline singleton."""
    global _pipeline
    if _pipeline is None:
        _pipeline = build_invoice_pipeline()
        logger.info("Invoice processing pipeline compiled")
    return _pipeline


async def process_invoice(
    image_bytes: bytes,
    trader_id: str,
    mime_type: str = "image/jpeg",
    source: str = "whatsapp",
    trader_state_code: str = None,
) -> Dict[str, Any]:
    """
    Process a single invoice through the full pipeline.

    This is the main entry point for invoice ingestion from any source
    (WhatsApp, email, direct upload).

    Args:
        image_bytes: Raw image/document bytes.
        trader_id: UUID of the trader.
        mime_type: MIME type of the input file.
        source: Ingestion source ('whatsapp', 'email', 'upload').
        trader_state_code: Buyer's state code for geographic fraud checks.

    Returns:
        Final pipeline state with all results.
    """
    pipeline = get_pipeline()

    initial_state: InvoicePipelineState = {
        "image_bytes": image_bytes,
        "mime_type": mime_type,
        "trader_id": trader_id,
        "source": source,
        "trader_state_code": trader_state_code,
        "errors": [],
    }

    logger.info("Starting invoice pipeline for trader=%s, source=%s", trader_id, source)

    result = await pipeline.ainvoke(initial_state)

    # Log summary
    extraction = result.get("extraction")
    itc = result.get("itc_result")
    fraud = result.get("fraud_result")
    errors = result.get("errors", [])

    logger.info(
        "Pipeline complete: invoice=%s, itc=%s, fraud_score=%s, errors=%d",
        extraction.invoice_number if extraction else "N/A",
        itc.status.value if itc else "N/A",
        fraud.total_score if fraud else "N/A",
        len(errors),
    )

    return result
