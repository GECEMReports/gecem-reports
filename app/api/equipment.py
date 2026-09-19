import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.equipment import Equipment
from app.schemas.equipment import EquipmentCreate, EquipmentResponse
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
