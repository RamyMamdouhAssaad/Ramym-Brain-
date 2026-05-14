"""Database connection pool for Supabase Postgres."""

import asyncpg
from src.config import SUPABASE_DB_URL

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    """Get or create the connection pool."""
    global _pool
    if _pool is None:
        if not SUPABASE_DB_URL:
            raise RuntimeError(
                "SUPABASE_DB_URL not set. Copy .env.example to .env and fill in your credentials."
            )
        _pool = await asyncpg.create_pool(
            SUPABASE_DB_URL,
            min_size=2,
            max_size=10,
            command_timeout=30,
        )
    return _pool


async def close_pool() -> None:
    """Close the connection pool."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None
