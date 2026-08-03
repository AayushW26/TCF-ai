"""
Authentication API — CA login, registration, and JWT management.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.config import get_settings
from app.models.auth import LoginRequest, RegisterRequest, TokenResponse, CAUser
from app.services.supabase_client import insert_row, get_rows

logger = logging.getLogger(__name__)
router = APIRouter()

# Password hashing
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Bearer token scheme
security = HTTPBearer()


def _hash_password(password: str) -> str:
    return pwd_context.hash(password)


def _verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def _create_token(ca_id: str, email: str) -> tuple[str, int]:
    """Create a JWT token. Returns (token, expires_in_seconds)."""
    settings = get_settings()
    expires_delta = timedelta(minutes=settings.jwt_expiry_minutes)
    expire = datetime.now(timezone.utc) + expires_delta

    payload = {
        "sub": ca_id,
        "email": email,
        "exp": expire,
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return token, int(expires_delta.total_seconds())


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> CAUser:
    """
    Dependency: extract and validate the JWT token, return the CA user.
    Inject this into any route that requires authentication.
    """
    settings = get_settings()
    token = credentials.credentials

    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        ca_id: str = payload.get("sub")
        if ca_id is None:
            raise HTTPException(status_code=401, detail="Invalid token payload")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    # Fetch user from DB
    users = await get_rows("ca_users", filters={"id": ca_id}, limit=1)
    if not users:
        raise HTTPException(status_code=401, detail="User not found")

    user = users[0]
    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="Account is disabled")

    return CAUser(
        id=user["id"],
        email=user["email"],
        full_name=user["full_name"],
        firm_name=user.get("firm_name"),
        phone=user.get("phone"),
        is_active=user["is_active"],
        created_at=user.get("created_at"),
    )


# ── Endpoints ────────────────────────────────────────────────


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(body: RegisterRequest):
    """Register a new CA account."""
    # Check if email already exists
    existing = await get_rows("ca_users", filters={"email": body.email}, limit=1)
    if existing:
        raise HTTPException(status_code=409, detail="Email already registered")

    # Create user
    user_data = {
        "email": body.email,
        "password_hash": _hash_password(body.password),
        "full_name": body.full_name,
        "firm_name": body.firm_name,
        "phone": body.phone,
    }
    created = await insert_row("ca_users", user_data)

    token, expires_in = _create_token(created["id"], created["email"])
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.post("/login", response_model=TokenResponse)
async def login(body: LoginRequest):
    """Authenticate a CA and return a JWT."""
    users = await get_rows("ca_users", filters={"email": body.email}, limit=1)
    if not users:
        raise HTTPException(status_code=401, detail="Invalid email or password")

    user = users[0]
    if not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    if not user.get("is_active"):
        raise HTTPException(status_code=403, detail="Account is disabled")

    token, expires_in = _create_token(user["id"], user["email"])
    return TokenResponse(access_token=token, expires_in=expires_in)


@router.get("/me", response_model=CAUser)
async def get_profile(current_user: CAUser = Depends(get_current_user)):
    """Get the current CA's profile."""
    return current_user
