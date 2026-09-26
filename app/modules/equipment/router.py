import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.modules.equipment.schemas import EquipmentCreate, EquipmentResponse, EquipmentUpdate
from app.modules.equipment import service as equipment_service

router = APIRouter(prefix="/equipment", tags=["equipment"])


@router.post("/", response_model=EquipmentResponse)
async def create_equipment(
    req: EquipmentCreate,
    db: AsyncSession = Depends(get_db),
):
    return await equipment_service.create_equipment(db, req)


@router.get("/", response_model=list[EquipmentResponse])
async def list_equipment(db: AsyncSession = Depends(get_db)):
    return await equipment_service.list_equipment(db)


@router.get("/{equipment_id}", response_model=EquipmentResponse)
async def get_equipment(equipment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    equipment = await equipment_service.get_equipment(db, equipment_id)
    if not equipment:
        raise HTTPException(404, "Equipment not found")
    return equipment


@router.patch("/{equipment_id}", response_model=EquipmentResponse)
async def update_equipment(
    equipment_id: uuid.UUID,
    req: EquipmentUpdate,
    db: AsyncSession = Depends(get_db),
):
    return await equipment_service.update_equipment(db, equipment_id, req)


@router.delete("/{equipment_id}")
async def delete_equipment(equipment_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    return await equipment_service.delete_equipment(db, equipment_id)
