"""
Wakeel وکیل — Database Layer
==============================
Manages the Supabase client lifecycle and provides FastAPI dependency
injection helpers for both the anon-key client (respects RLS) and the
service-role client (admin operations, bypasses RLS).

Usage in a router:
    from database import get_supabase, get_supabase_admin

    @router.get("/example")
    async def example(db: AsyncClient = Depends(get_supabase)):
        result = await db.table("queries").select("*").execute()
        return result.data
"""

from typing import AsyncGenerator

from fastapi import Depends, HTTPException, status
from loguru import logger
from supabase import acreate_client
from supabase.client import AsyncClient

from config import settings

# ─────────────────────────────────────────────────────────────────────────────
# Module-level client references (initialised in lifespan)
# ─────────────────────────────────────────────────────────────────────────────
_supabase_client: AsyncClient | None = None
_supabase_admin_client: AsyncClient | None = None


async def init_supabase() -> None:
    """
    Called once from the FastAPI lifespan on startup.
    Creates both the anon-key client and the service-role admin client.
    """
    global _supabase_client, _supabase_admin_client

    if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
        logger.warning(
            "Supabase credentials missing — DB operations will fail. "
            "Check your .env file."
        )
        return

    _supabase_client = await acreate_client(
        settings.SUPABASE_URL,
        settings.SUPABASE_KEY,
    )
    logger.info("  ✓  Supabase anon client initialised")

    # Service-role client is optional; only created if key is provided
    if settings.SUPABASE_SERVICE_ROLE_KEY:
        _supabase_admin_client = await acreate_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_ROLE_KEY,
        )
        logger.info("  ✓  Supabase service-role client initialised")
    else:
        logger.warning(
            "  ⚠  SUPABASE_SERVICE_ROLE_KEY not set — "
            "admin operations will be unavailable."
        )


# ─────────────────────────────────────────────────────────────────────────────
# Dependency injection helpers
# ─────────────────────────────────────────────────────────────────────────────
async def get_supabase() -> AsyncGenerator[AsyncClient, None]:
    """
    FastAPI dependency: yields the anon-key Supabase client.
    This client respects Row Level Security — use for all user-facing operations.

    Example:
        @router.get("/queries")
        async def list_queries(db: AsyncClient = Depends(get_supabase)):
            ...
    """
    if _supabase_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database client not initialised. Check server startup logs.",
        )
    yield _supabase_client


async def get_supabase_admin() -> AsyncGenerator[AsyncClient, None]:
    """
    FastAPI dependency: yields the service-role Supabase client.
    ⚠  BYPASSES RLS — use ONLY for admin/system operations, never in
    user-facing endpoints that act on user-supplied data.
    """
    if _supabase_admin_client is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Admin DB client not available. Set SUPABASE_SERVICE_ROLE_KEY.",
        )
    yield _supabase_admin_client


# ─────────────────────────────────────────────────────────────────────────────
# Utility: safe execute wrapper
# ─────────────────────────────────────────────────────────────────────────────
async def safe_execute(query_builder):
    """
    Wraps a supabase-py query builder call with error handling.
    Returns (data, error) tuple — never raises, caller decides how to handle.

    Usage:
        data, error = await safe_execute(
            db.table("queries").select("*").eq("user_id", uid)
        )
        if error:
            raise HTTPException(500, detail=str(error))
    """
    try:
        result = await query_builder.execute()
        return result.data, None
    except Exception as exc:
        logger.error(f"Supabase query error: {exc}")
        return None, exc
