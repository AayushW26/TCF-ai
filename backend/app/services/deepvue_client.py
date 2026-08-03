"""
DeepVue.tech API client — GSTIN validation and information retrieval.

Results are cached in Redis (24h TTL) to avoid redundant API calls.
"""

import logging
from datetime import datetime
from typing import Optional

import httpx
from pydantic import BaseModel

from app.config import get_settings
from app.services.redis_client import cache_get_json, cache_set_json

logger = logging.getLogger(__name__)

DEEPVUE_BASE_URL = "https://production.deepvue.tech/v1"


class GSTINInfo(BaseModel):
    """Parsed GSTIN information from DeepVue."""
    gstin: str
    legal_name: Optional[str] = None
    trade_name: Optional[str] = None
    registration_date: Optional[str] = None  # DD/MM/YYYY from API
    status: Optional[str] = None  # "Active", "Cancelled", etc.
    business_type: Optional[str] = None  # "Regular", "Composition", etc.
    state_code: Optional[str] = None
    state_name: Optional[str] = None
    is_valid: bool = False
    is_active: bool = False
    days_since_registration: Optional[int] = None


async def validate_gstin(gstin: str) -> GSTINInfo:
    """
    Validate a GSTIN via DeepVue.tech API.

    Results are cached in Redis for 24 hours.

    Args:
        gstin: 15-character GSTIN to validate.

    Returns:
        GSTINInfo with details about the GSTIN.
    """
    # Check cache first
    cache_key = f"gstin:{gstin}"
    cached = await cache_get_json(cache_key)
    if cached:
        logger.debug("GSTIN %s found in cache", gstin)
        return GSTINInfo(**cached)

    # Basic format validation
    if not gstin or len(gstin) != 15:
        return GSTINInfo(gstin=gstin, is_valid=False)

    settings = get_settings()

    try:
        async with httpx.AsyncClient(timeout=15) as client:
            response = await client.get(
                f"{DEEPVUE_BASE_URL}/verification/gstin",
                params={"gstin": gstin},
                headers={
                    "x-api-key": settings.deepvue_api_key,
                    "client-id": settings.deepvue_client_id,
                },
            )
            response.raise_for_status()
            data = response.json()

        # Parse the API response
        result_data = data.get("data", {})

        # Calculate days since registration
        days_since = None
        reg_date_str = result_data.get("registration_date")
        if reg_date_str:
            try:
                reg_date = datetime.strptime(reg_date_str, "%d/%m/%Y")
                days_since = (datetime.now() - reg_date).days
            except ValueError:
                pass

        status = result_data.get("status", "")
        info = GSTINInfo(
            gstin=gstin,
            legal_name=result_data.get("legal_name"),
            trade_name=result_data.get("trade_name"),
            registration_date=reg_date_str,
            status=status,
            business_type=result_data.get("constitution_of_business"),
            state_code=gstin[:2],  # First 2 digits of GSTIN = state code
            state_name=result_data.get("state"),
            is_valid=True,
            is_active=status.lower() == "active" if status else False,
            days_since_registration=days_since,
        )

        # Cache for 24 hours
        await cache_set_json(cache_key, info.model_dump(), ttl=86400)

        logger.info(
            "GSTIN %s validated: %s (%s), registered %s",
            gstin, info.legal_name, info.status, info.registration_date,
        )

        return info

    except httpx.HTTPStatusError as e:
        logger.error("DeepVue API error for GSTIN %s: %s", gstin, e.response.status_code)
        return GSTINInfo(gstin=gstin, is_valid=False)

    except Exception as e:
        logger.error("DeepVue API call failed for GSTIN %s: %s", gstin, e)
        return GSTINInfo(gstin=gstin, is_valid=False)
