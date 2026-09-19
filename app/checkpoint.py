import asyncio
import sys

from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from app.config import settings

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

_context = None
_checkpointer: AsyncPostgresSaver | None = None


def checkpoint_dsn() -> str:
    """Return the psycopg DSN required by AsyncPostgresSaver."""
    if settings.CHECKPOINT_DATABASE_URL:
        return settings.CHECKPOINT_DATABASE_URL
    return settings.DATABASE_URL.replace("postgresql+asyncpg://", "postgresql://", 1)


async def start_checkpointer() -> AsyncPostgresSaver:
    global _context, _checkpointer
    _context = AsyncPostgresSaver.from_conn_string(checkpoint_dsn())
    _checkpointer = await _context.__aenter__()
    return _checkpointer


async def stop_checkpointer() -> None:
    global _context, _checkpointer
    if _context is not None:
        await _context.__aexit__(None, None, None)
    _context = None
    _checkpointer = None


def get_checkpointer() -> AsyncPostgresSaver:
    if _checkpointer is None:
        raise RuntimeError("Postgres checkpointer is not initialized")
    return _checkpointer
