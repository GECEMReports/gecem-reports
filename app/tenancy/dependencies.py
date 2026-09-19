import uuid

from sqlalchemy import event
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import async_session
from app.tenancy.middleware import current_tenant_id


async def get_tenant_db(tenant_id: uuid.UUID | None = None) -> AsyncSession:
    tid = tenant_id or current_tenant_id.get()
    async with async_session() as session:
        if tid:
            await session.execute(
                __import__("sqlalchemy").text(f"SET LOCAL app.tenant_id = '{tid}'")
            )
        yield session
