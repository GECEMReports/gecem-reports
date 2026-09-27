"""Equipment domain service (thin).

Encapsulates the Equipment operations, moved verbatim from the former
`app/api/equipment.py` router. No logic changes.

TEMPORAL DEPENDENCY (documented): `delete_equipment` reads `Falla` and
`ProcedimientoReparacion` from `app.models.falla` for the delete guard.
It will be switched to Failures/Repairs ports once those domains are
modularized. Failures and Repairs themselves are NOT modularized here.
"""

import uuid

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.repairs.models import ProcedimientoReparacion  # TEMPORAL: hasta puerto de Repairs
from app.modules.failures.models import Falla  # TEMPORAL: hasta puerto de Failures
from app.modules.equipment.models import Equipment
from app.modules.equipment.schemas import (
    EquipmentCreate,
    EquipmentResponse,
    EquipmentUpdate,
)
from app.tenancy.middleware import current_tenant_id


async def _require_tenant_id():
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")
    return tenant_id


async def list_equipment(db: AsyncSession) -> list[Equipment]:
    tenant_id = await _require_tenant_id()

    result = await db.execute(
        select(Equipment).where(Equipment.tenant_id == tenant_id)
    )
    return result.scalars().all()


async def get_equipment(db: AsyncSession, equipment_id: uuid.UUID) -> Equipment | None:
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(Equipment).where(
            Equipment.id == equipment_id,
            Equipment.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def get_equipment_or_404(db: AsyncSession, equipment_id: uuid.UUID) -> Equipment:
    equipment = await get_equipment(db, equipment_id)
    if not equipment:
        raise HTTPException(404, "Equipment not found")
    return equipment


async def create_equipment(db: AsyncSession, req: EquipmentCreate) -> Equipment:
    tenant_id = await _require_tenant_id()

    equipment = Equipment(
        tenant_id=tenant_id,
        brand=req.brand,
        model=req.model,
        serial_number=req.serial_number,
        equipment_type=req.equipment_type,
        hours=req.hours,
        year=req.year,
        client_id=str(req.client_id) if req.client_id else None,
        notes=req.notes,
    )
    db.add(equipment)
    await db.commit()
    await db.refresh(equipment)
    return equipment


async def update_equipment(
    db: AsyncSession, equipment_id: uuid.UUID, req: EquipmentUpdate
) -> Equipment:
    tenant_id = await _require_tenant_id()

    result = await db.execute(
        select(Equipment).where(
            Equipment.id == equipment_id,
            Equipment.tenant_id == tenant_id,
        )
    )
    equipment = result.scalar_one_or_none()
    if not equipment:
        raise HTTPException(404, "Equipment not found")

    # Check serial_number uniqueness if being changed
    if req.serial_number and req.serial_number != equipment.serial_number:
        existing = await db.execute(
            select(Equipment).where(
                Equipment.serial_number == req.serial_number,
                Equipment.tenant_id == tenant_id,
                Equipment.id != equipment_id,
            )
        )
        if existing.scalar_one_or_none():
            raise HTTPException(409, "Serial number already exists")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(equipment, field, value)

    await db.commit()
    await db.refresh(equipment)
    return equipment


async def delete_equipment(db: AsyncSession, equipment_id: uuid.UUID) -> dict:
    tenant_id = await _require_tenant_id()

    result = await db.execute(
        select(Equipment).where(
            Equipment.id == equipment_id,
            Equipment.tenant_id == tenant_id,
        )
    )
    equipment = result.scalar_one_or_none()
    if not equipment:
        raise HTTPException(404, "Equipment not found")

    # Check for related records
    fallas_count = await db.execute(
        select(func.count()).where(Falla.equipment_id == equipment_id)
    )
    reparaciones_count = await db.execute(
        select(func.count()).where(ProcedimientoReparacion.equipment_id == equipment_id)
    )

    fallas = fallas_count.scalar() or 0
    reparaciones = reparaciones_count.scalar() or 0

    if fallas > 0 or reparaciones > 0:
        raise HTTPException(
            409,
            "El sistema no permite eliminar maquinas con historial"
        )

    await db.delete(equipment)
    await db.commit()
    return {"message": "Equipo eliminado"}


__all__ = [
    "EquipmentResponse",
    "create_equipment",
    "delete_equipment",
    "get_equipment",
    "get_equipment_or_404",
    "list_equipment",
    "update_equipment",
]
