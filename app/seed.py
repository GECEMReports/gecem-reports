import asyncio
import uuid

from app.database import async_session
from app.models.base import TenantModel
from app.models.user import User
from app.modules.equipment.models import Equipment
from app.models.client import Client
from app.modules.diagnosis.models import Report
from app.utils.auth import hash_password


async def seed():
    # Solo siembra datos. El esquema lo administra Alembic:
    #   alembic upgrade head
    async with async_session() as session:
        # Create test tenant
        tenant = TenantModel(name="Taller Demo", slug="demo", plan="free")
        session.add(tenant)
        await session.flush()

        # Create admin user
        user = User(
            tenant_id=tenant.id,
            email="admin@demo.com",
            hashed_password=hash_password("demo1234"),
            full_name="Mecanico Demo",
            role="admin",
        )
        session.add(user)

        # Create test client
        client = Client(
            tenant_id=tenant.id,
            name="Constructora ABC",
            company="ABC S.A. de C.V.",
            email="contacto@abc.com",
            phone="+52 55 1234 5678",
        )
        session.add(client)
        await session.flush()

        # Create test equipment
        equipment = Equipment(
            tenant_id=tenant.id,
            brand="CAT",
            model="320",
            serial_number="CAT0320XLHD01234",
            equipment_type="excavator",
            hours=5200,
            year=2019,
            client_id=str(client.id),
            notes="Excavadora para obra civil",
        )
        session.add(equipment)

        await session.commit()

        print(f"Tenant: {tenant.slug} (ID: {tenant.id})")
        print(f"User: admin@demo.com / demo1234")
        print(f"Client: {client.name} (ID: {client.id})")
        print(f"Equipment: {equipment.brand} {equipment.model} (ID: {equipment.id})")


if __name__ == "__main__":
    asyncio.run(seed())
