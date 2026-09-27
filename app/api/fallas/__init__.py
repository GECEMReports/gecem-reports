import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.falla import Falla, FallaFoto
from app.modules.equipment.service import get_equipment_or_404
from app.schemas.falla import (
    FallaCreate,
    FallaResponse,
    FallaUpdate,
)
from app.tenancy.middleware import current_tenant_id

router = APIRouter(prefix="/fallas", tags=["fallas"])

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "media" / "fallas"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/", response_model=FallaResponse)
async def create_falla(req: FallaCreate, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Convert string IDs to UUID
    equipment_uuid = uuid.UUID(req.equipment_id)
    diagnosis_uuid = uuid.UUID(req.diagnosis_id) if req.diagnosis_id else None

    # Verify equipment belongs to tenant
    await get_equipment_or_404(db, equipment_uuid)

    falla = Falla(
        tenant_id=tenant_id,
        equipment_id=equipment_uuid,
        diagnosis_id=diagnosis_uuid,
        parte=req.parte,
        pieza=req.pieza,
        descripcion=req.descripcion,
        causa_raiz=req.causa_raiz,
        prioridad=req.prioridad,
        notas=req.notas,
    )
    db.add(falla)
    await db.commit()
    await db.refresh(falla)

    # Reload with fotos relationship
    result = await db.execute(
        select(Falla).where(Falla.id == falla.id).options(selectinload(Falla.fotos))
    )
    return result.scalar_one()


@router.get("/", response_model=list[FallaResponse])
async def list_fallas(equipment_id: str | None = None, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    query = select(Falla).where(Falla.tenant_id == tenant_id).options(selectinload(Falla.fotos))
    if equipment_id:
        query = query.where(Falla.equipment_id == equipment_id)
    query = query.order_by(Falla.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


@router.get("/{falla_id}", response_model=FallaResponse)
async def get_falla(falla_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(Falla)
        .where(Falla.id == falla_id, Falla.tenant_id == tenant_id)
        .options(selectinload(Falla.fotos))
    )
    falla = result.scalar_one_or_none()
    if not falla:
        raise HTTPException(404, "Falla not found")
    return falla


@router.patch("/{falla_id}", response_model=FallaResponse)
async def update_falla(falla_id: uuid.UUID, req: FallaUpdate, db: AsyncSession = Depends(get_db)):
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(Falla)
        .where(Falla.id == falla_id, Falla.tenant_id == tenant_id)
        .options(selectinload(Falla.fotos))
    )
    falla = result.scalar_one_or_none()
    if not falla:
        raise HTTPException(404, "Falla not found")

    update_data = req.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(falla, field, value)

    await db.commit()
    await db.refresh(falla)
    return falla


@router.post("/{falla_id}/fotos")
async def upload_foto(
    falla_id: uuid.UUID,
    file: UploadFile = File(...),
    descripcion: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Verify falla belongs to tenant
    result = await db.execute(
        select(Falla).where(Falla.id == falla_id, Falla.tenant_id == tenant_id)
    )
    falla = result.scalar_one_or_none()
    if not falla:
        raise HTTPException(404, "Falla not found")

    # Save file
    ext = Path(file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    # Save to DB
    foto = FallaFoto(
        tenant_id=tenant_id,
        falla_id=falla_id,
        filename=filename,
        filepath=str(filepath),
        descripcion=descripcion,
    )
    db.add(foto)
    await db.commit()

    return {"id": foto.id, "filename": filename, "message": "Foto subida"}
