"""Repairs domain service (thin).

Encapsulates the Reparaciones operations, moved verbatim from the former
`app/api/reparaciones.py` router. No logic changes.

Equipment and Failures are consumed exclusively through their public
services (`get_equipment_or_404` / `get_falla_or_404`). `cotizacion_id`
is stored without existence validation (DB FK enforces it), as before.
"""

import uuid
from pathlib import Path

from fastapi import HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.equipment.service import get_equipment_or_404
from app.modules.failures.service import get_falla_or_404
from app.modules.repairs.models import PasoFoto, PasoReparacion, ProcedimientoReparacion
from app.modules.repairs.schemas import (
    CompletarProcedimientoRequest,
    PasoCreate,
    ProcedimientoCreate,
)
from app.tenancy.middleware import current_tenant_id

UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "media" / "pasos"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


async def create_procedimiento(
    db: AsyncSession, req: ProcedimientoCreate
) -> ProcedimientoReparacion:
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Verify equipment belongs to tenant
    equipment_uuid = uuid.UUID(req.equipment_id)
    await get_equipment_or_404(db, equipment_uuid)

    # Verify falla if provided (optional for independent reparaciones)
    falla_uuid = None
    if req.falla_id:
        falla_uuid = uuid.UUID(req.falla_id)
        await get_falla_or_404(db, falla_uuid)

    proc = ProcedimientoReparacion(
        tenant_id=tenant_id,
        equipment_id=equipment_uuid,
        falla_id=falla_uuid,
        cotizacion_id=uuid.UUID(req.cotizacion_id) if req.cotizacion_id else None,
        descripcion=req.descripcion,
        tipo=req.tipo,
        notas=req.notas,
    )
    db.add(proc)
    await db.commit()
    await db.refresh(proc)

    # Reload with pasos
    result = await db.execute(
        select(ProcedimientoReparacion)
        .where(ProcedimientoReparacion.id == proc.id)
        .options(selectinload(ProcedimientoReparacion.pasos).selectinload(PasoReparacion.fotos))
    )
    return result.scalar_one()


async def list_procedimientos(
    db: AsyncSession,
    equipment_id: str | None = None,
    falla_id: str | None = None,
) -> list[ProcedimientoReparacion]:
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    query = (
        select(ProcedimientoReparacion)
        .where(ProcedimientoReparacion.tenant_id == tenant_id)
        .options(selectinload(ProcedimientoReparacion.pasos).selectinload(PasoReparacion.fotos))
    )
    if equipment_id:
        query = query.where(ProcedimientoReparacion.equipment_id == uuid.UUID(equipment_id))
    if falla_id:
        query = query.where(ProcedimientoReparacion.falla_id == uuid.UUID(falla_id))
    query = query.order_by(ProcedimientoReparacion.created_at.desc())

    result = await db.execute(query)
    return result.scalars().all()


async def get_procedimiento(
    db: AsyncSession, proc_id: uuid.UUID
) -> ProcedimientoReparacion | None:
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(ProcedimientoReparacion)
        .where(ProcedimientoReparacion.id == proc_id, ProcedimientoReparacion.tenant_id == tenant_id)
        .options(selectinload(ProcedimientoReparacion.pasos).selectinload(PasoReparacion.fotos))
    )
    return result.scalar_one_or_none()


async def get_procedimiento_or_404(
    db: AsyncSession, proc_id: uuid.UUID
) -> ProcedimientoReparacion:
    proc = await get_procedimiento(db, proc_id)
    if not proc:
        raise HTTPException(404, "Procedimiento not found")
    return proc


async def add_paso(
    db: AsyncSession, proc_id: uuid.UUID, req: PasoCreate
) -> PasoReparacion:
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Verify proc belongs to tenant
    result = await db.execute(
        select(ProcedimientoReparacion).where(
            ProcedimientoReparacion.id == proc_id,
            ProcedimientoReparacion.tenant_id == tenant_id,
        )
    )
    proc = result.scalar_one_or_none()
    if not proc:
        raise HTTPException(404, "Procedimiento not found")

    # Get next step number
    count_result = await db.execute(
        select(PasoReparacion).where(PasoReparacion.procedimiento_id == proc_id)
    )
    existing = count_result.scalars().all()
    next_num = len(existing) + 1

    paso = PasoReparacion(
        tenant_id=tenant_id,
        procedimiento_id=proc_id,
        numero_paso=next_num,
        descripcion=req.descripcion,
        tiempo_minutos=req.tiempo_minutos,
    )
    db.add(paso)
    await db.commit()
    await db.refresh(paso)

    # Reload with fotos relationship for response serialization
    result = await db.execute(
        select(PasoReparacion)
        .where(PasoReparacion.id == paso.id)
        .options(selectinload(PasoReparacion.fotos))
    )
    return result.scalar_one()


async def add_paso_foto(
    db: AsyncSession, proc_id: uuid.UUID, paso_id: uuid.UUID, file: UploadFile
) -> PasoFoto:
    tenant_id = current_tenant_id.get()
    if not tenant_id:
        raise HTTPException(400, "Tenant context required")

    # Verify paso belongs to proc and tenant
    result = await db.execute(
        select(PasoReparacion).where(
            PasoReparacion.id == paso_id,
            PasoReparacion.procedimiento_id == proc_id,
            PasoReparacion.tenant_id == tenant_id,
        )
    )
    paso = result.scalar_one_or_none()
    if not paso:
        raise HTTPException(404, "Paso not found")

    # Save file
    ext = Path(file.filename).suffix or ".jpg"
    filename = f"{uuid.uuid4()}{ext}"
    filepath = UPLOAD_DIR / filename

    with open(filepath, "wb") as f:
        content = await file.read()
        f.write(content)

    foto = PasoFoto(
        tenant_id=tenant_id,
        paso_id=paso_id,
        filename=filename,
        filepath=str(filepath),
    )
    db.add(foto)
    await db.commit()

    return PasoFoto(id=foto.id, filename=filename, filepath=str(filepath))


async def complete_procedimiento(
    db: AsyncSession, proc_id: uuid.UUID, req: CompletarProcedimientoRequest
) -> ProcedimientoReparacion:
    tenant_id = current_tenant_id.get()
    result = await db.execute(
        select(ProcedimientoReparacion).where(
            ProcedimientoReparacion.id == proc_id,
            ProcedimientoReparacion.tenant_id == tenant_id,
        )
    )
    proc = result.scalar_one_or_none()
    if not proc:
        raise HTTPException(404, "Procedimiento not found")

    proc.status = "completado"
    proc.tiempo_total_horas = req.tiempo_total_horas
    if req.notas:
        proc.notas = req.notas
    await db.commit()

    # Reload with pasos
    result = await db.execute(
        select(ProcedimientoReparacion)
        .where(ProcedimientoReparacion.id == proc_id)
        .options(selectinload(ProcedimientoReparacion.pasos).selectinload(PasoReparacion.fotos))
    )
    return result.scalar_one()


__all__ = [
    "add_paso",
    "add_paso_foto",
    "complete_procedimiento",
    "create_procedimiento",
    "get_procedimiento",
    "get_procedimiento_or_404",
    "list_procedimientos",
]
