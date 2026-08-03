"""
Gemini 2.5 Flash client — invoice extraction via Vision API.

Uses the google-genai SDK for structured JSON output.
"""

import json
import logging
import base64
from typing import Optional

from google import genai
from google.genai import types

from app.config import get_settings
from app.models.invoice import InvoiceExtraction

logger = logging.getLogger(__name__)

# Module-level client
_client: Optional[genai.Client] = None


def get_gemini_client() -> genai.Client:
    """Lazy-initialise and return the Gemini client."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = genai.Client(api_key=settings.gemini_api_key)
    return _client


# System prompt for structured invoice extraction
EXTRACTION_SYSTEM_PROMPT = """You are an expert Indian GST invoice data extractor.
Given an image of an invoice (which may be a crumpled thermal receipt, handwritten bill,
scanned PDF, or blurry photo), extract ALL the following fields into a JSON object.

Output ONLY valid JSON with these fields:
{
  "supplier_name": "string or null",
  "supplier_gstin": "string (15-char GSTIN) or null",
  "invoice_number": "string or null",
  "invoice_date": "YYYY-MM-DD string or null",
  "place_of_supply": "state name or code or null",
  "reverse_charge": false,
  "line_items": [
    {
      "description": "string",
      "hsn_code": "string or null",
      "quantity": number or null,
      "rate": number or null,
      "taxable_value": number or null,
      "cgst_rate": number,
      "sgst_rate": number,
      "igst_rate": number,
      "cgst": number,
      "sgst": number,
      "igst": number,
      "cess": number
    }
  ],
  "total_taxable_value": number or null,
  "cgst": number,
  "sgst": number,
  "igst": number,
  "cess": number,
  "total_amount": number or null,
  "confidence_score": number between 0 and 1
}

Rules:
- For amounts, use numbers without currency symbols.
- For GSTIN, validate the 15-character format: 2 digits (state) + 10 chars (PAN) + 1 digit + 'Z' + 1 checksum.
- If a field is not visible or illegible, set it to null.
- confidence_score should reflect overall extraction quality (1.0 = perfect, 0.5 = many uncertain fields).
- Always output valid JSON. No markdown, no explanations.
"""


async def extract_invoice(image_bytes: bytes, mime_type: str = "image/jpeg") -> InvoiceExtraction:
    """
    Extract structured invoice data from an image using Gemini 2.5 Flash Vision.

    Args:
        image_bytes: Raw image bytes.
        mime_type: MIME type of the image (image/jpeg, image/png, application/pdf).

    Returns:
        InvoiceExtraction model with extracted data.
    """
    client = get_gemini_client()

    # Encode image for the API
    image_part = types.Part.from_bytes(
        data=image_bytes,
        mime_type=mime_type,
    )

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[
                types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(EXTRACTION_SYSTEM_PROMPT),
                        image_part,
                        types.Part.from_text(
                            "Extract all invoice data from this image. Return ONLY valid JSON."
                        ),
                    ],
                )
            ],
            config=types.GenerateContentConfig(
                temperature=0.1,
                max_output_tokens=4096,
                response_mime_type="application/json",
            ),
        )

        # Parse the JSON response
        raw_text = response.text.strip()

        # Handle markdown code fences if present
        if raw_text.startswith("```"):
            raw_text = raw_text.split("\n", 1)[1]  # Remove first line
            raw_text = raw_text.rsplit("```", 1)[0]  # Remove last fence

        data = json.loads(raw_text)
        extraction = InvoiceExtraction(**data)

        logger.info(
            "Invoice extracted: supplier=%s, number=%s, confidence=%.2f",
            extraction.supplier_name,
            extraction.invoice_number,
            extraction.confidence_score,
        )

        return extraction

    except json.JSONDecodeError as e:
        logger.error("Failed to parse Gemini response as JSON: %s", e)
        return InvoiceExtraction(confidence_score=0.0)

    except Exception as e:
        logger.error("Gemini extraction failed: %s", e)
        return InvoiceExtraction(confidence_score=0.0)


async def extract_invoice_from_base64(
    base64_data: str, mime_type: str = "image/jpeg"
) -> InvoiceExtraction:
    """Extract invoice from base64-encoded image data."""
    image_bytes = base64.b64decode(base64_data)
    return await extract_invoice(image_bytes, mime_type)
