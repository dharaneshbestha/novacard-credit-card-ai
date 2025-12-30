import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None


async def connect_db():
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(dsn=settings.DATABASE_URL, min_size=1, max_size=5)


async def close_db():
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


async def get_pool() -> asyncpg.Pool:
    if _pool is None:
        await connect_db()
    assert _pool is not None
    return _pool
