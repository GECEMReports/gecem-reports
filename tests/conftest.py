"""ETAPA 0 — Congelar comportamiento del dominio Diagnosis.

Este conftest NO modifica codigo productivo. Solo redirige la aplicacion
hacia una base de datos de pruebas aislada (gecem_reports_test) ANTES de
importar cualquier modulo de `app`, de modo que los tests nunca tocan la
base de desarrollo ni la de produccion.
"""

import os
import sys
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

os.environ["DATABASE_URL"] = (
    "postgresql+asyncpg://postgres:postgres@localhost:5432/gecem_reports_test"
)

import httpx  # noqa: E402

import app.models  # noqa: F401,E402  (registra todos los modelos en Base.metadata)
import app.database as app_database  # noqa: E402
import app.agents.tools as app_tools  # noqa: E402
from app.main import app  # noqa: E402
from app.models.base import Base, TenantModel  # noqa: E402
from app.models.equipment import Equipment  # noqa: E402
from app.models.report import Report  # noqa: E402

# NullPool: cada test de anyio corre en su propio event loop; un pool
# persistente reutilizaria conexiones atadas al loop anterior
# ("attached to a different loop"). Solo afecta al proceso de tests.
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

engine = create_async_engine(os.environ["DATABASE_URL"], poolclass=NullPool)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
app_database.engine = engine
app_database.async_session = async_session
app_tools.async_session = async_session


@pytest.fixture(params=["asyncio"])
def anyio_backend(request):
    return request.param


@pytest.fixture(scope="session", autouse=True)
def _dispose_engine():
    yield
    import asyncio

    asyncio.run(engine.dispose())


@pytest.fixture
async def test_db():
    """Crea tablas, limpia y siembra tenant + equipment. Limpia reports al salir."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with async_session() as session:
        from sqlalchemy import delete

        await session.execute(delete(Report))
        await session.execute(delete(Equipment))
        await session.execute(delete(TenantModel))
        await session.commit()

        tenant = TenantModel(name="Tenant Test", slug=f"test-{uuid.uuid4().hex[:8]}")
        session.add(tenant)
        await session.flush()

        equipment = Equipment(
            tenant_id=tenant.id,
            brand="CAT",
            model="320D",
            serial_number="SN-TEST-001",
            equipment_type="excavator",
            hours=1250.0,
            year=2019,
            client_id=None,
            notes=None,
        )
        session.add(equipment)
        await session.flush()
        await session.commit()

        data = {
            "tenant_id": tenant.id,
            "equipment_id": equipment.id,
            "brand": equipment.brand,
            "model": equipment.model,
        }

    yield data

    async with async_session() as session:
        from sqlalchemy import delete

        await session.execute(delete(Report))
        await session.execute(delete(Equipment))
        await session.execute(delete(TenantModel))
        await session.commit()


@pytest.fixture
async def client():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


def tenant_headers(tenant_id) -> dict:
    return {"X-Tenant-ID": str(tenant_id)}
