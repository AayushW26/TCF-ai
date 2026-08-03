"""
Supabase client — singleton initialisation and helper methods.

Uses the service role key to bypass RLS (all access control is handled
at the API layer via JWT auth).
"""

import logging
from typing import Any, Dict, List, Optional

from supabase import create_client, Client

logger = logging.getLogger(__name__)

# Module-level singleton
_client: Optional[Client] = None


def init_supabase(url: str, service_key: str) -> Client:
    """Initialise the global Supabase client. Called once at app startup."""
    global _client
    _client = create_client(url, service_key)
    logger.info("Supabase client initialised")
    return _client


def get_supabase() -> Client:
    """Return the initialised Supabase client."""
    if _client is None:
        raise RuntimeError("Supabase client not initialised — call init_supabase() first")
    return _client


def close_supabase() -> None:
    """Cleanup (no-op for supabase-py, but keeps the interface consistent)."""
    global _client
    _client = None
    logger.info("Supabase client closed")


# ── Convenience helpers ──────────────────────────────────────


async def insert_row(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Insert a single row and return the created record."""
    response = get_supabase().table(table).insert(data).execute()
    return response.data[0] if response.data else {}


async def insert_rows(table: str, data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Insert multiple rows and return created records."""
    if not data:
        return []
    response = get_supabase().table(table).insert(data).execute()
    return response.data or []


async def get_rows(
    table: str,
    filters: Optional[Dict[str, Any]] = None,
    select: str = "*",
    order_by: Optional[str] = None,
    limit: Optional[int] = None,
    offset: Optional[int] = None,
) -> List[Dict[str, Any]]:
    """Fetch rows with optional filters, ordering, and pagination."""
    query = get_supabase().table(table).select(select)

    if filters:
        for key, value in filters.items():
            query = query.eq(key, value)

    if order_by:
        # Support "column.desc" syntax
        if order_by.endswith(".desc"):
            query = query.order(order_by.replace(".desc", ""), desc=True)
        else:
            query = query.order(order_by)

    if limit:
        query = query.limit(limit)

    if offset:
        query = query.offset(offset)

    response = query.execute()
    return response.data or []


async def get_row_by_id(table: str, row_id: str, select: str = "*") -> Optional[Dict[str, Any]]:
    """Fetch a single row by its UUID id."""
    response = get_supabase().table(table).select(select).eq("id", row_id).limit(1).execute()
    return response.data[0] if response.data else None


async def update_row(table: str, row_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update a row by id and return the updated record."""
    response = get_supabase().table(table).update(data).eq("id", row_id).execute()
    return response.data[0] if response.data else {}


async def upsert_row(table: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Upsert a row (insert or update on conflict)."""
    response = get_supabase().table(table).upsert(data).execute()
    return response.data[0] if response.data else {}


async def delete_row(table: str, row_id: str) -> bool:
    """Delete a row by id."""
    get_supabase().table(table).delete().eq("id", row_id).execute()
    return True


async def count_rows(table: str, filters: Optional[Dict[str, Any]] = None) -> int:
    """Count rows matching filters."""
    query = get_supabase().table(table).select("id", count="exact")
    if filters:
        for key, value in filters.items():
            query = query.eq(key, value)
    response = query.execute()
    return response.count or 0


async def get_rows_in(
    table: str,
    column: str,
    values: List[Any],
    select: str = "*",
) -> List[Dict[str, Any]]:
    """Fetch rows where column value is IN the given list."""
    if not values:
        return []
    response = get_supabase().table(table).select(select).in_(column, values).execute()
    return response.data or []
