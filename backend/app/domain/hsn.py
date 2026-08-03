"""
HSN (Harmonized System of Nomenclature) Code Validator.

Validates HSN code format, looks up descriptions from a built-in
reference table, and maps to ITC-relevant categories.
"""

import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from functools import lru_cache

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class HSNValidationResult(BaseModel):
    """Result of HSN code validation."""
    hsn_code: str
    is_valid: bool
    description: Optional[str] = None
    chapter: Optional[str] = None
    category: Optional[str] = None  # goods / services
    is_blocked_itc: bool = False
    blocked_reason: Optional[str] = None


# HSN format: 4, 6, or 8 digits
HSN_PATTERN = re.compile(r"^\d{4}(\d{2})?(\d{2})?$")
# SAC format: 4 or 6 digits starting with 99
SAC_PATTERN = re.compile(r"^99\d{2}(\d{2})?$")


@lru_cache(maxsize=1)
def _load_hsn_reference() -> Dict[str, dict]:
    """Load the HSN reference data from the JSON file."""
    data_path = Path(__file__).parent.parent / "data" / "hsn_codes.json"
    try:
        with open(data_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Index by HSN code
        return {entry["code"]: entry for entry in data}
    except FileNotFoundError:
        logger.warning("HSN reference data file not found at %s", data_path)
        return {}
    except json.JSONDecodeError as e:
        logger.error("Failed to parse HSN reference data: %s", e)
        return {}


def validate_hsn(hsn_code: str) -> HSNValidationResult:
    """
    Validate a single HSN/SAC code.

    Args:
        hsn_code: The HSN or SAC code to validate.

    Returns:
        HSNValidationResult with validation details.
    """
    if not hsn_code:
        return HSNValidationResult(
            hsn_code="",
            is_valid=False,
            description="Empty HSN code",
        )

    code = hsn_code.strip()

    # Check format
    is_sac = code.startswith("99")
    if is_sac:
        is_valid_format = bool(SAC_PATTERN.match(code))
        category = "services"
    else:
        is_valid_format = bool(HSN_PATTERN.match(code))
        category = "goods"

    if not is_valid_format:
        return HSNValidationResult(
            hsn_code=code,
            is_valid=False,
            description=f"Invalid {'SAC' if is_sac else 'HSN'} code format (expected 4/6/8 digits)",
        )

    # Look up in reference data
    ref = _load_hsn_reference()
    entry = ref.get(code)

    # Try prefix match (4-digit chapter)
    if not entry and len(code) > 4:
        entry = ref.get(code[:4])

    description = entry.get("description") if entry else None
    chapter = code[:2] if len(code) >= 2 else None

    # Check if this HSN is in a blocked ITC category
    is_blocked, blocked_reason = _check_blocked_hsn(code)

    return HSNValidationResult(
        hsn_code=code,
        is_valid=True,
        description=description,
        chapter=chapter,
        category=category,
        is_blocked_itc=is_blocked,
        blocked_reason=blocked_reason,
    )


def validate_hsn_list(hsn_codes: List[str]) -> List[HSNValidationResult]:
    """Validate a list of HSN codes."""
    return [validate_hsn(code) for code in hsn_codes]


# HSN prefixes that are commonly associated with blocked ITC under §17(5)
BLOCKED_HSN_MAP: List[Tuple[str, str, str]] = [
    # (prefix, category, reason)
    ("8702", "Motor Vehicles", "§17(5)(a) — Motor vehicles ≤13 seats"),
    ("8703", "Motor Vehicles", "§17(5)(a) — Motor vehicles ≤13 seats"),
    ("9963", "Food & Catering", "§17(5)(b)(i) — Food, beverages, outdoor catering"),
    ("9966", "Transport", "§17(5)(b)(iii) — Rent-a-cab services"),
    ("9971", "Insurance", "§17(5)(b)(iii) — Life/health insurance"),
    ("9954", "Construction", "§17(5)(c) — Works contract for immovable property"),
    ("9602", "Personal Care", "§17(5)(b)(i) — Beauty treatment"),
]


def _check_blocked_hsn(hsn_code: str) -> Tuple[bool, Optional[str]]:
    """Check if an HSN code falls into a blocked ITC category."""
    for prefix, _category, reason in BLOCKED_HSN_MAP:
        if hsn_code.startswith(prefix):
            return True, reason
    return False, None


def get_chapter_description(chapter_code: str) -> Optional[str]:
    """Get the description for a 2-digit HSN chapter code."""
    chapters = {
        "01": "Live Animals", "02": "Meat and Edible Meat Offal",
        "03": "Fish", "04": "Dairy Produce", "05": "Products of Animal Origin",
        "06": "Live Trees and Plants", "07": "Edible Vegetables",
        "08": "Edible Fruit and Nuts", "09": "Coffee, Tea, Spices",
        "10": "Cereals", "11": "Products of Milling Industry",
        "12": "Oil Seeds", "13": "Lac, Gums, Resins",
        "15": "Animal/Vegetable Fats", "16": "Preparations of Meat/Fish",
        "17": "Sugars", "18": "Cocoa", "19": "Preparations of Cereals",
        "20": "Preparations of Vegetables/Fruit",
        "21": "Miscellaneous Edible Preparations",
        "22": "Beverages, Spirits, Vinegar",
        "24": "Tobacco", "25": "Salt, Sulphur, Earth, Stone",
        "27": "Mineral Fuels, Oils", "28": "Inorganic Chemicals",
        "29": "Organic Chemicals", "30": "Pharmaceutical Products",
        "32": "Dyes, Paints", "33": "Essential Oils, Cosmetics",
        "34": "Soap, Wax", "38": "Chemical Products",
        "39": "Plastics", "40": "Rubber",
        "44": "Wood", "48": "Paper",
        "52": "Cotton", "54": "Man-Made Filaments",
        "61": "Knitted Apparel", "62": "Woven Apparel",
        "63": "Textile Articles", "64": "Footwear",
        "68": "Stone, Cement", "69": "Ceramic Products",
        "70": "Glass", "71": "Precious Metals",
        "72": "Iron and Steel", "73": "Articles of Iron/Steel",
        "76": "Aluminium", "82": "Tools",
        "83": "Base Metal Articles", "84": "Machinery",
        "85": "Electrical Machinery", "87": "Vehicles",
        "90": "Optical/Measuring Instruments",
        "94": "Furniture", "95": "Toys, Games",
        "96": "Miscellaneous Manufactured Articles",
    }
    return chapters.get(chapter_code)
