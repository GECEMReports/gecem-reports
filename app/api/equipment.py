import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.equipment import Equipment
from app.models.falla import Falla, ProcedimientoReparacion
from app.schemas.equipment import EquipmentCreate, EquipmentResponse, EquipmentUpdate
from app.tenancy.middleware import current_tenant_id

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.post("/", response_model=EquipmentResponse)
async def create_equipment(
    req: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

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


@router.get("/", response_model=list[EquipmentResponse])
async def list_equipment(db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    result = await db.execute(
        select(Equipment).where(Equipment.tenant_id == tenant_id)
    )
    return result.scalars().all()


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(equipment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(Equipment).where(
            Equipment.id == equipment_id,
            Equipment.tenant_id == tenant_id,
        )
    )
    equipment = result.scalar_one_or_none()
    if not equipment:
        raise HTTPException(404, "Equipment not found")
    return equipment


@router.patch("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: uuid.UUID,
    req: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

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


@router.delete("/{equipment_id}")
async def delete_equipment(equipment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

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
