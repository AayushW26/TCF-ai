"""
Pydantic models for trader data.
"""

from datetime import datetime
from typing import Optional
from enum import Enum

from pydantic import BaseModel


class OnboardingState(str, Enum):
    INIT = "INIT"
    NAME_RECEIVED = "NAME_RECEIVED"
    GSTIN_RECEIVED = "GSTIN_RECEIVED"
    CONFIRMED = "CONFIRMED"
    ACTIVE = "ACTIVE"


class TraderCreate(BaseModel):
    """Request body for creating a new trader."""
    business_name: str
    gstin: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    state_code: Optional[str] = None


class TraderResponse(BaseModel):
    """Trader data returned from the API."""
    id: str
    ca_id: str
    business_name: str
    gstin: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None
    munim_email: Optional[str] = None
    state_code: Optional[str] = None
    onboarding_state: OnboardingState = OnboardingState.INIT
    is_active: bool = True
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TraderBrief(BaseModel):
    """Minimal trader info for lists."""
    id: str
    business_name: str
    gstin: Optional[str] = None
    phone: Optional[str] = None
    is_active: bool = True
